# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/management/commands/update_trends.py
# Description:  Management command to compute and cache a "trend score" for
#               every active product. Run via cron every hour:
#                 python manage.py update_trends
#
#               Trend score formula (higher = more trending):
#                 score = views_in_last_7_days * 0.3
#                       + order_count_in_last_7_days * 1.5
#                       + wishlist_adds_in_last_7_days * 0.8
#                       + avg_rating * 0.5
#
#               Results are written to ProductTrendScore (one row per product).
#               The home page and category pages can then sort by trend_score
#               without a slow real-time computation.
# =============================================================================

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Avg
from datetime import timedelta

from shop.models import Product, ViewedProduct, OrderItem, WishlistItem, ProductTrendScore


class Command(BaseCommand):
    """Recalculate and cache the trend score for all active products."""

    help = 'Recalculate ProductTrendScore for all active products'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=7)

        # Fetch counts for the last 7 days in bulk (one query each)
        view_counts = (
            ViewedProduct.objects.filter(viewed_at__gte=cutoff)
            .values('product_id')
            .annotate(cnt=Count('id'))
        )
        view_map = {r['product_id']: r['cnt'] for r in view_counts}

        order_counts = (
            OrderItem.objects.filter(order__created_at__gte=cutoff)
            .values('product_id')
            .annotate(cnt=Count('id'))
        )
        order_map = {r['product_id']: r['cnt'] for r in order_counts}

        wishlist_counts = (
            WishlistItem.objects.filter(created_at__gte=cutoff)
            .values('product_id')
            .annotate(cnt=Count('id'))
        )
        wishlist_map = {r['product_id']: r['cnt'] for r in wishlist_counts}

        rating_avgs = (
            Product.objects.filter(is_active=True, is_approved=True)
            .annotate(avg_r=Avg('ratings__rating'))
            .values('id', 'avg_r')
        )
        rating_map = {r['id']: (r['avg_r'] or 0) for r in rating_avgs}

        products = Product.objects.filter(is_active=True, is_approved=True)
        updated = 0
        created = 0

        for product in products:
            views   = view_map.get(product.id, 0)
            orders  = order_map.get(product.id, 0)
            wishlists = wishlist_map.get(product.id, 0)
            rating  = rating_map.get(product.id, 0)

            score = (
                views    * 0.3 +
                orders   * 1.5 +
                wishlists * 0.8 +
                rating   * 0.5
            )

            obj, is_new = ProductTrendScore.objects.update_or_create(
                product=product,
                defaults={'score': round(score, 4)}
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Trend scores updated: {updated} updated, {created} created.'
            )
        )
