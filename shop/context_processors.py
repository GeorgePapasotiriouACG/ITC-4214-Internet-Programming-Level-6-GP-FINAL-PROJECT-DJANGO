# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/context_processors.py
# Description:  Django context processors that inject global template variables
#               into every template on every request. Provides the cart item
#               count for the navbar badge and the root category list for the
#               navigation mega-menu.
# =============================================================================

from .models import Cart, Category


def cart_context(request):
    """
    Inject `cart_count` into every template context.
    - For logged-in users: looks up the user's database Cart record.
    - For guests: looks up a Cart matching the current session key.
    The count is shown as a badge on the cart icon in the navbar.
    Wrapped in a broad except so a DB error never breaks page rendering.
    """
    cart_count = 0
    try:
        if request.user.is_authenticated:
            # Retrieve the unique cart linked to this user account
            cart = Cart.objects.filter(user=request.user).first()
        else:
            # For anonymous visitors we use the session key as the cart identifier
            session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key, user=None).first() if session_key else None
        if cart:
            cart_count = cart.get_item_count()
    except Exception:
        # Silently swallow any DB error — cart badge just shows 0
        pass
    return {'cart_count': cart_count}


def site_context(request):
    """
    Inject global site information and top-level category tree.
    `root_categories` is prefetch_related('children') so subcategory dropdowns
    don't trigger N+1 queries in the navbar template.
    """
    # Only fetch active categories; prefetch children to avoid N+1 in the nav
    root_categories = Category.objects.filter(parent=None, is_active=True).prefetch_related('children')
    return {
        'site_name': 'TrendMart',
        'site_tagline': 'Shop the Trend, Live the Style',
        'root_categories': root_categories,
    }
