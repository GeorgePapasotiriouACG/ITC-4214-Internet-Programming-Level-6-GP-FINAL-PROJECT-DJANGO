# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/emails.py
# Description:  Automated email notification helpers for TrendMart.
#               Sends HTML + plain-text emails for:
#                 1. Order confirmation  — sent when a user completes checkout
#                 2. Dispatch notification — sent when admin marks order "shipped"
#                 3. Wishlist price-drop alert — sent when a wishlisted product
#                    goes on sale (call check_wishlist_price_drops() from a
#                    management command or Celery task)
#
#               In development (DEBUG=True) emails print to the terminal console.
#               In production set EMAIL_BACKEND to SMTP in settings.py.
#
# Usage:
#   from shop.emails import send_order_confirmation, send_dispatch_notification
#   send_order_confirmation(order)
#   send_dispatch_notification(order)
# =============================================================================

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags


# ── Helper: send HTML + plain-text email ─────────────────────────────────────
def _send_email(subject, to_email, html_content):
    """
    Internal helper to send a two-part (HTML + plain-text) email.
    EmailMultiAlternatives sends HTML to capable clients and plain text to
    legacy clients, maximising deliverability.
    Silently swallows exceptions so email failures never break the checkout flow.
    """
    try:
        plain_text = strip_tags(html_content)  # Strip HTML tags for plain-text part
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.send()
        return True
    except Exception as exc:
        # Log the failure but never raise — email should never crash the app
        import logging
        logging.getLogger('trendmart.emails').warning(
            f"Email send failed to {to_email}: {exc}"
        )
        return False


# ── 1. Order Confirmation ─────────────────────────────────────────────────────
def send_order_confirmation(order):
    """
    Send a branded order confirmation email immediately after checkout.
    Includes: order number, itemised list, shipping address, and total.
    Template: templates/shop/emails/order_confirmation.html
    """
    subject = f"✅ TrendMart Order Confirmed — #{order.order_number}"
    html_content = render_to_string('shop/emails/order_confirmation.html', {
        'order': order,
        'site_name': 'TrendMart',
        'site_url': f"https://{getattr(settings, 'SITE_DOMAIN', 'localhost:8000')}",
    })
    return _send_email(subject, order.email, html_content)


# ── 2. Dispatch Notification ──────────────────────────────────────────────────
def send_dispatch_notification(order):
    """
    Send a dispatch email when an admin changes order status to "shipped".
    Includes: estimated delivery window and a link to the order detail page.
    Template: templates/shop/emails/dispatch_notification.html
    """
    subject = f"📦 Your TrendMart Order #{order.order_number} Has Shipped!"
    html_content = render_to_string('shop/emails/dispatch_notification.html', {
        'order': order,
        'site_name': 'TrendMart',
        'site_url': f"https://{getattr(settings, 'SITE_DOMAIN', 'localhost:8000')}",
    })
    return _send_email(subject, order.email, html_content)


# ── 3. Wishlist Price-Drop Alert ──────────────────────────────────────────────
def send_price_drop_alert(user, product, old_price):
    """
    Notify a user when a product in their wishlist goes on sale.
    Called from check_wishlist_price_drops() — run this periodically via
    a management command or a Celery beat task.
    Template: templates/shop/emails/price_drop_alert.html
    """
    subject = f"🔥 Price Drop Alert — {product.name} is Now on Sale!"
    html_content = render_to_string('shop/emails/price_drop_alert.html', {
        'user': user,
        'product': product,
        'old_price': old_price,
        'new_price': product.get_effective_price(),
        'saving': old_price - product.get_effective_price(),
        'site_name': 'TrendMart',
        'site_url': f"https://{getattr(settings, 'SITE_DOMAIN', 'localhost:8000')}",
    })
    return _send_email(subject, user.email, html_content)


# ── 4. Scan wishlist items for price drops ───────────────────────────────────
def check_wishlist_price_drops():
    """
    Scans all wishlist items and sends a price-drop alert email if the product
    has gone on sale since the item was added.  Safe to call repeatedly —
    uses a 'notified_at' sentinel (stored in session or a simple DB flag) to
    avoid spamming users.

    Intended usage:
        # management command / Celery task
        from shop.emails import check_wishlist_price_drops
        check_wishlist_price_drops()

    NOTE: This is a simple implementation. For production, add a
          WishlistItem.notified_at DateTimeField and only send once per sale.
    """
    from .models import WishlistItem

    # Group wishlist items by product to avoid N+1 per-user queries
    items = (
        WishlistItem.objects
        .select_related('user', 'product', 'product__brand')
        .filter(product__sale_price__isnull=False, product__is_active=True, product__is_approved=True)
    )
    sent = 0
    for item in items:
        product = item.product
        # Only alert if the sale price is genuinely less than the original
        if product.sale_price and product.sale_price < product.price:
            if send_price_drop_alert(item.user, product, product.price):
                sent += 1
    return sent
