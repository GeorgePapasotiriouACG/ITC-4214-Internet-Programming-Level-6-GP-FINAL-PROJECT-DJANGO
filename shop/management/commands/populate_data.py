import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User
from shop.models import Product

class Command(BaseCommand):
    help = 'Populate the database with a complete dataset of products, reviews, variants, and test users.'

    def handle(self, *args, **options):
        self.stdout.write('Checking database status...')
        
        # We check if there are a significant number of products or users to decide if we should seed
        if Product.objects.count() > 30 and User.objects.count() > 5:
            self.stdout.write(self.style.SUCCESS('Database already fully populated. Skipping...'))
            return

        # Find the seed file located at the root of the project
        seed_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
            'seed_data.json'
        )
        
        if os.path.exists(seed_file):
            self.stdout.write(f'Found comprehensive seed file at {seed_file}...')
            self.stdout.write('Loading complete dataset (products, variants, reviews, users, etc.)...')
            
            try:
                # Load the JSON fixture directly into the DB
                call_command('loaddata', seed_file)
                
                # Report on what was created
                user_count = User.objects.count()
                product_count = Product.objects.count()
                from shop.models import ProductRating, ProductVariant
                rating_count = ProductRating.objects.count()
                variant_count = ProductVariant.objects.count()
                
                self.stdout.write(f"  - Users: {user_count}")
                self.stdout.write(f"  - Products: {product_count}")
                self.stdout.write(f"  - Variants: {variant_count}")
                self.stdout.write(f"  - Ratings/Reviews: {rating_count}")
                
                self.stdout.write(self.style.SUCCESS('\nSUCCESS: Database populated with complete TrendMart snapshot!'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error loading seed data: {str(e)}'))
        else:
            self.stdout.write(self.style.ERROR(
                f'Seed file not found: {seed_file}\n'
                'Please ensure seed_data.json is deployed with your project code.'
            ))
