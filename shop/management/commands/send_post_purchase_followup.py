"""
Management command: send_post_purchase_followup

Sends a proactive AI chat notification to users whose orders were placed
48 hours ago, asking if they need any help with their purchase.

Run via cron / Windows Task Scheduler:
    python manage.py send_post_purchase_followup

Recommended schedule: every hour (so the 48h window is accurate to within ~1h)
    Cron: 0 * * * * cd /path/to/project && python manage.py send_post_purchase_followup
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from shop.models import Order, Notification


class Command(BaseCommand):
    help = 'Send post-purchase follow-up notifications to users 48 hours after order placement.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be done without actually creating notifications.',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=48,
            help='Hours after order placement to send the follow-up (default: 48).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hours = options['hours']

        now = timezone.now()
        window_start = now - timedelta(hours=hours + 1)
        window_end   = now - timedelta(hours=hours)

        orders = Order.objects.filter(
            created_at__gte=window_start,
            created_at__lt=window_end,
            user__isnull=False,
            status__in=['pending', 'processing', 'shipped', 'delivered'],
        ).select_related('user').prefetch_related('items')

        sent = 0
        skipped = 0

        for order in orders:
            user = order.user
            if not user:
                skipped += 1
                continue

            already_notified = Notification.objects.filter(
                user=user,
                notification_type='system',
                title='How is your order going? 👋',
                message__icontains=order.order_number,
            ).exists()

            if already_notified:
                skipped += 1
                continue

            item_names = ', '.join(
                item.product_name for item in order.items.all()[:2]
            )
            if order.items.count() > 2:
                item_names += f' and {order.items.count() - 2} more item(s)'

            message = (
                f"Hi {user.first_name or user.username}! 👋 It's been 48 hours since you ordered "
                f"{item_names} (Order #{order.order_number}). "
                f"How's everything going? If you have any questions about your purchase, "
                f"I'm here to help! Just open the chat below."
            )

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'[DRY RUN] Would notify {user.username} about order {order.order_number}'
                    )
                )
            else:
                Notification.objects.create(
                    user=user,
                    notification_type='system',
                    title='How is your order going? 👋',
                    message=message,
                    link='/dashboard/',
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Notified {user.username} about order {order.order_number}'
                    )
                )
            sent += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. Notifications sent: {sent} | Skipped (already notified / no user): {skipped}'
            )
        )
