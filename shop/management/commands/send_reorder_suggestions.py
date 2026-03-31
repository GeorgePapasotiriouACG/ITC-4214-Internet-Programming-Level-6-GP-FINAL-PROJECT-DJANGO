"""
Management command: send_reorder_suggestions

Scans orders delivered 30 days ago and sends a restock reminder notification
to users who ordered consumable items (tagged as 'consumable' or 'refillable'),
or as a general "it's been a month" reminder for all delivered orders.

Run via cron / Windows Task Scheduler:
    python manage.py send_reorder_suggestions

Recommended schedule: once daily at 09:00
    Cron: 0 9 * * * cd /path/to/project && python manage.py send_reorder_suggestions
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from shop.models import Order, OrderItem, Notification


class Command(BaseCommand):
    help = 'Send 30-day reorder/restock suggestions to users for their delivered orders.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be done without actually creating notifications.',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Days after delivery to send the reorder suggestion (default: 30).',
        )
        parser.add_argument(
            '--all-products',
            action='store_true',
            help='Suggest reorder for ALL products, not just consumable/tagged ones.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days = options['days']
        all_products = options['all_products']

        now = timezone.now()
        window_start = now - timedelta(days=days + 1)
        window_end   = now - timedelta(days=days)

        orders = Order.objects.filter(
            created_at__gte=window_start,
            created_at__lt=window_end,
            status='delivered',
            user__isnull=False,
        ).select_related('user').prefetch_related('items__product')

        sent = 0
        skipped = 0

        for order in orders:
            user = order.user
            if not user:
                skipped += 1
                continue

            already_notified = Notification.objects.filter(
                user=user,
                notification_type='recommendation',
                title__icontains='reorder',
                message__icontains=order.order_number,
            ).exists()

            if already_notified:
                skipped += 1
                continue

            reorder_items = []
            for item in order.items.all():
                if not item.product:
                    continue
                if all_products:
                    reorder_items.append(item)
                else:
                    tags = (item.product.tags or '').lower()
                    if any(t in tags for t in ('consumable', 'refillable', 'monthly', 'supplement', 'skincare', 'cleaning')):
                        reorder_items.append(item)

            if not reorder_items and not all_products:
                skipped += 1
                continue

            if reorder_items:
                item_names = ', '.join(i.product_name for i in reorder_items[:2])
                if len(reorder_items) > 2:
                    item_names += f' and {len(reorder_items) - 2} more'
                message = (
                    f"Hey {user.first_name or user.username}! 🛒 It's been {days} days since your order "
                    f"#{order.order_number}. Time to restock {item_names}? "
                    f"Click here to reorder with one tap!"
                )
            else:
                first_item = order.items.first()
                item_name = first_item.product_name if first_item else 'your recent purchase'
                message = (
                    f"Hey {user.first_name or user.username}! 📦 It's been {days} days since your order "
                    f"#{order.order_number} ({item_name}). "
                    f"Loved it? Reorder anytime from your order history!"
                )

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'[DRY RUN] Would send reorder suggestion to {user.username} '
                        f'for order {order.order_number}'
                    )
                )
            else:
                Notification.objects.create(
                    user=user,
                    notification_type='recommendation',
                    title=f'Time to reorder? 🛒 (Order #{order.order_number})',
                    message=message,
                    link='/dashboard/orders/',
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Sent reorder suggestion to {user.username} for order {order.order_number}'
                    )
                )
            sent += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. Suggestions sent: {sent} | Skipped: {skipped}'
            )
        )
