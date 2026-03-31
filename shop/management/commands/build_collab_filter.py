"""
Management command: build_collab_filter
Builds a co-purchase matrix for the "Customers who bought this also bought…" recommender.

Run nightly via:
    python manage.py build_collab_filter

Or via Windows Task Scheduler / cron:
    0 3 * * * cd /path/to/project && python manage.py build_collab_filter
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from collections import defaultdict

from shop.models import OrderItem, Product


class Command(BaseCommand):
    help = 'Builds a co-purchase matrix for collaborative filtering recommendations.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-support', type=int, default=2,
            help='Minimum number of co-purchases to count as a recommendation (default: 2)'
        )
        parser.add_argument(
            '--top-k', type=int, default=8,
            help='Number of similar products to store per product (default: 8)'
        )

    def handle(self, *args, **options):
        min_support = options['min_support']
        top_k = options['top_k']

        self.stdout.write('Building co-purchase matrix...')

        order_items = (
            OrderItem.objects
            .select_related('product', 'order')
            .values('order__id', 'product__id')
        )

        order_products = defaultdict(set)
        for row in order_items:
            order_products[row['order__id']].add(row['product__id'])

        co_count = defaultdict(lambda: defaultdict(int))
        for pid_set in order_products.values():
            pid_list = list(pid_set)
            for i, a in enumerate(pid_list):
                for b in pid_list[i+1:]:
                    co_count[a][b] += 1
                    co_count[b][a] += 1

        updated = 0
        for product_id, neighbors in co_count.items():
            top_neighbors = sorted(
                ((pid, cnt) for pid, cnt in neighbors.items() if cnt >= min_support),
                key=lambda x: -x[1]
            )[:top_k]

            if not top_neighbors:
                continue

            try:
                product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                continue

            similar_ids = [pid for pid, _ in top_neighbors]
            product.collab_recs = ','.join(str(i) for i in similar_ids)
            product.save(update_fields=['collab_recs'])

            from django.core.cache import cache
            cache.set(f'collab_recs_{product_id}', similar_ids, timeout=86400)

            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. Computed recommendations for {updated} products '
            f'(min_support={min_support}, top_k={top_k}).'
        ))
