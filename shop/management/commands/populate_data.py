from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal
from shop.models import UserProfile, RetailerProfile, Category, Brand, Product
from django.utils.text import slugify
import uuid


class Command(BaseCommand):
    help = 'Populate the database with sample data for TrendMart'

    def handle(self, *args, **options):
        self.stdout.write('Creating test users...')
        self.create_test_users()
        
        self.stdout.write('Creating categories...')
        self.create_categories()
        
        self.stdout.write('Creating brands...')
        self.create_brands()
        
        self.stdout.write('Creating products...')
        self.create_products()
        
        self.stdout.write(self.style.SUCCESS('Successfully populated TrendMart with sample data!'))

    def create_test_users(self):
        # Create admin user
        if not User.objects.filter(username='george_admin').exists():
            admin_user = User.objects.create_user(
                username='george_admin',
                email='george@trendmart.com',
                first_name='George',
                last_name='Papasotiriou',
                password='admin123',
                is_staff=True,
                is_superuser=True
            )
            UserProfile.objects.create(
                user=admin_user,
                role='admin',
                phone='+30 210 123 4567',
                address='123 E-Commerce Street',
                city='Athens',
                country='Greece',
                postal_code='12345'
            )
        
        # Create test customers
        customers_data = [
            ('john_doe', 'john@email.com', 'John', 'Doe', '+1 234 567 8900', 'New York', 'USA', '10001'),
            ('jane_smith', 'jane@email.com', 'Jane', 'Smith', '+1 234 567 8901', 'Los Angeles', 'USA', '90001'),
            ('mike_wilson', 'mike@email.com', 'Mike', 'Wilson', '+1 234 567 8902', 'Chicago', 'USA', '60007'),
            ('sarah_brown', 'sarah@email.com', 'Sarah', 'Brown', '+1 234 567 8903', 'Houston', 'USA', '77001'),
            ('david_jones', 'david@email.com', 'David', 'Jones', '+1 234 567 8904', 'Phoenix', 'USA', '85001'),
        ]
        
        for username, email, first, last, phone, city, country, postal in customers_data:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first,
                    last_name=last,
                    password='customer123'
                )
                UserProfile.objects.create(
                    user=user,
                    role='customer',
                    phone=phone,
                    address=f'{first} {last} Residence',
                    city=city,
                    country=country,
                    postal_code=postal
                )
        
        # Create test retailers
        retailers_data = [
            ('tech_gadgets', 'tech@retailer.com', 'Tech', 'Gadgets Inc', 'Premium electronics and gadgets retailer', '456 Tech Avenue, Silicon Valley, CA 94025', 'https://techgadgets.com'),
            ('fashion_hub', 'fashion@retailer.com', 'Fashion', 'Hub', 'Trendy clothing and accessories store', '789 Style Boulevard, New York, NY 10018', 'https://fashionhub.com'),
            ('sports_world', 'sports@retailer.com', 'Sports', 'World', 'Athletic gear and sports equipment', '321 Stadium Drive, Los Angeles, CA 90001', 'https://sportsworld.com'),
        ]
        
        for username, email, first, last, desc, address, website in retailers_data:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first,
                    last_name=last,
                    password='retailer123'
                )
                profile = UserProfile.objects.create(
                    user=user,
                    role='retailer',
                    phone='+1 234 567 8900',
                    address=address,
                    city='Business City',
                    country='USA',
                    postal_code='12345'
                )
                RetailerProfile.objects.create(
                    user=user,
                    business_name=f"{first} {last}",
                    business_description=desc,
                    business_address=address,
                    website=website,
                    is_approved=True
                )

    def create_categories(self):
        categories = [
            # Main categories
            ('Electronics', None, 'Latest electronic devices and gadgets', '💻', 1),
            ('Fashion', None, 'Clothing, shoes, and accessories', '👕', 2),
            ('Home & Garden', None, 'Everything for your home and garden', '🏠', 3),
            ('Sports & Outdoors', None, 'Sports equipment and outdoor gear', '⚽', 4),
            ('Books & Media', None, 'Books, movies, and music', '📚', 5),
            ('Beauty & Health', None, 'Skincare, makeup, and health products', '💄', 6),
            ('Toys & Games', None, 'Toys and games for all ages', '🎮', 7),
            ('Automotive', None, 'Car parts and accessories', '🚗', 8),
            
            # Electronics subcategories
            ('Smartphones', 'Electronics', 'Mobile phones and accessories', '📱', 1),
            ('Laptops', 'Electronics', 'Laptop computers and accessories', '💻', 2),
            ('Audio', 'Electronics', 'Headphones, speakers, and audio equipment', '🎧', 3),
            ('Cameras', 'Electronics', 'Digital cameras and photography gear', '📷', 4),
            ('Gaming', 'Electronics', 'Gaming consoles and accessories', '🎮', 5),
            
            # Fashion subcategories
            ("Men's Clothing", 'Fashion', "Clothing for men", '👔', 1),
            ("Women's Clothing", 'Fashion', "Clothing for women", '👗', 2),
            ('Shoes', 'Fashion', 'Footwear for all occasions', '👟', 3),
            ('Accessories', 'Fashion', 'Bags, watches, and fashion accessories', '👜', 4),
            
            # Home & Garden subcategories
            ('Furniture', 'Home & Garden', 'Home furniture and decor', '🪑', 1),
            ('Kitchen', 'Home & Garden', 'Kitchen appliances and tools', '🍳', 2),
            ('Garden', 'Home & Garden', 'Garden tools and supplies', '🌻', 3),
        ]
        
        category_map = {}
        
        for name, parent_name, description, icon, order in categories:
            if not Category.objects.filter(name=name).exists():
                parent = None
                if parent_name:
                    parent = category_map.get(parent_name)
                
                category = Category.objects.create(
                    name=name,
                    parent=parent,
                    description=description,
                    icon=icon,
                    order=order,
                    slug=slugify(name)
                )
                category_map[name] = category
            else:
                category_map[name] = Category.objects.get(name=name)

    def create_brands(self):
        brands = [
            ('Apple', 'Premium technology and electronics'),
            ('Samsung', 'Innovative electronics and mobile devices'),
            ('Nike', 'Athletic footwear and apparel'),
            ('Adidas', 'Sports clothing and accessories'),
            ('Sony', 'Electronics and entertainment'),
            ('LG', 'Home electronics and appliances'),
            ('Canon', 'Imaging and optical products'),
            ('Dell', 'Computers and technology'),
            ('HP', 'Computing and printing solutions'),
            ('Microsoft', 'Software and technology'),
            ('Puma', 'Sports and lifestyle products'),
            ('Under Armour', 'Athletic performance gear'),
            ('Levi\'s', 'Denim and casual clothing'),
            ('Zara', 'Fast fashion clothing'),
            ('H&M', 'Fashion clothing and accessories'),
            ('Gucci', 'Luxury fashion and accessories'),
            ('Prada', 'High-end fashion products'),
            ('Ray-Ban', 'Eyewear and sunglasses'),
            ('Bose', 'Audio equipment and headphones'),
            ('JBL', 'Professional audio equipment'),
        ]
        
        for name, description in brands:
            if not Brand.objects.filter(name=name).exists():
                Brand.objects.create(
                    name=name,
                    description=description,
                    is_active=True,
                    slug=slugify(name)
                )

    def create_products(self):
        # Get categories and brands
        smartphones = Category.objects.get(name='Smartphones')
        laptops = Category.objects.get(name='Laptops')
        audio = Category.objects.get(name='Audio')
        cameras = Category.objects.get(name='Cameras')
        gaming = Category.objects.get(name='Gaming')
        mens_clothing = Category.objects.get(name="Men's Clothing")
        womens_clothing = Category.objects.get(name="Women's Clothing")
        shoes = Category.objects.get(name='Shoes')
        accessories = Category.objects.get(name='Accessories')
        furniture = Category.objects.get(name='Furniture')
        kitchen = Category.objects.get(name='Kitchen')
        garden = Category.objects.get(name='Garden')
        
        # Get brands
        apple = Brand.objects.get(name='Apple')
        samsung = Brand.objects.get(name='Samsung')
        nike = Brand.objects.get(name='Nike')
        adidas = Brand.objects.get(name='Adidas')
        sony = Brand.objects.get(name='Sony')
        canon = Brand.objects.get(name='Canon')
        dell = Brand.objects.get(name='Dell')
        hp = Brand.objects.get(name='HP')
        microsoft = Brand.objects.get(name='Microsoft')
        puma = Brand.objects.get(name='Puma')
        levis = Brand.objects.get(name='Levi\'s')
        zara = Brand.objects.get(name='Zara')
        gucci = Brand.objects.get(name='Gucci')
        rayban = Brand.objects.get(name='Ray-Ban')
        bose = Brand.objects.get(name='Bose')
        jbl = Brand.objects.get(name='JBL')
        
        # Get retailers
        tech_retailer = User.objects.get(username='tech_gadgets')
        fashion_retailer = User.objects.get(username='fashion_hub')
        sports_retailer = User.objects.get(username='sports_world')
        
        products = [
            # Smartphones
            ('iPhone 15 Pro', smartphones, apple, tech_retailer, 999.99, 899.99, 'Latest iPhone with titanium design', 'Space Gray, Silver, Gold, Blue Titanium', '128GB,256GB,512GB,1TB', 50, True),
            ('Samsung Galaxy S24 Ultra', smartphones, samsung, tech_retailer, 1199.99, 1099.99, 'Premium Android smartphone with S Pen', 'Phantom Black, Phantom White, Phantom Violet, Phantom Yellow', '256GB,512GB,1TB', 45, True),
            ('iPhone 14', smartphones, apple, tech_retailer, 699.99, 599.99, 'Previous generation iPhone', 'Midnight, Starlight, Blue, Purple, Red', '128GB,256GB,512GB', 30, False),
            ('Samsung Galaxy A54', smartphones, samsung, tech_retailer, 449.99, None, 'Mid-range Android smartphone', 'Awesome Lime, Awesome Graphite, Awesome Violet', '128GB,256GB', 60, False),
            
            # Laptops
            ('MacBook Pro 16"', laptops, apple, tech_retailer, 2499.99, 2299.99, 'Powerful laptop for professionals', 'Space Gray, Silver', '512GB SSD,1TB SSD,2TB SSD,4TB SSD', 25, True),
            ('Dell XPS 15', laptops, dell, tech_retailer, 1799.99, 1699.99, 'High-performance Windows laptop', 'Platinum Silver', '256GB SSD,512GB SSD,1TB SSD,2TB SSD', 35, True),
            ('HP Spectre x360', laptops, hp, tech_retailer, 1499.99, None, 'Convertible laptop with touchscreen', 'Nightfall Black, Natural Silver', '256GB SSD,512GB SSD,1TB SSD', 40, False),
            ('Microsoft Surface Laptop 5', laptops, microsoft, tech_retailer, 1299.99, 1199.99, 'Premium ultrabook with touch display', 'Sage, Platinum, Black, Sandstone', '256GB SSD,512GB SSD,1TB SSD', 30, False),
            
            # Audio
            ('AirPods Pro 2', audio, apple, tech_retailer, 249.99, 199.99, 'Wireless earbuds with noise cancellation', 'White', 'One Size', 80, True),
            ('Sony WH-1000XM5', audio, sony, tech_retailer, 399.99, 349.99, 'Premium noise-canceling headphones', 'Black, Silver', 'One Size', 45, True),
            ('Bose QuietComfort 45', audio, bose, tech_retailer, 329.99, None, 'Comfortable noise-canceling headphones', 'Black, White', 'One Size', 55, False),
            ('JBL Flip 6', audio, jbl, tech_retailer, 129.99, 99.99, 'Portable Bluetooth speaker', 'Black, White, Blue, Red, Green, Pink', 'One Size', 100, False),
            
            # Cameras
            ('Canon EOS R6 Mark II', cameras, canon, tech_retailer, 2499.99, 2299.99, 'Full-frame mirrorless camera', 'Black', 'Body Only, With Kit Lens', 20, True),
            ('Sony Alpha A7 IV', cameras, sony, tech_retailer, 2498.99, None, 'Versatile full-frame camera', 'Black', 'Body Only, With Kit Lens', 18, False),
            
            # Gaming
            ('PlayStation 5', gaming, sony, sports_retailer, 499.99, 449.99, 'Next-gen gaming console', 'White, Black', 'Standard, Digital Edition', 15, True),
            ('Xbox Series X', gaming, microsoft, sports_retailer, 499.99, None, 'Powerful gaming console', 'Black', 'One Size', 12, False),
            
            # Men's Clothing
            ('Nike Air Max 270', shoes, nike, sports_retailer, 150.00, 120.00, 'Comfortable running shoes', 'Black, White, Blue, Red', '7,7.5,8,8.5,9,9.5,10,10.5,11,11.5,12', 60, True),
            ('Adidas Ultraboost 22', shoes, adidas, sports_retailer, 190.00, 170.00, 'Premium running shoes', 'Core Black, Cloud White, Solar Red', '7,7.5,8,8.5,9,9.5,10,10.5,11,11.5,12', 45, True),
            ('Levi\'s 501 Original Jeans', mens_clothing, levis, fashion_retailer, 79.50, None, 'Classic straight-fit jeans', 'Various Washes', '28,29,30,31,32,33,34,36,38,40', 80, False),
            ('Puma RS-X³', shoes, puma, sports_retailer, 110.00, 89.99, 'Retro-inspired sneakers', 'White, Black, Blue', '7,7.5,8,8.5,9,9.5,10,10.5,11,11.5,12', 55, False),
            
            # Women's Clothing
            ('Zara Floral Dress', womens_clothing, zara, fashion_retailer, 59.99, 39.99, 'Summer floral print dress', 'Pink, Blue, Yellow', 'XS,S,M,L,XL', 40, True),
            ('Nike Sports Bra', womens_clothing, nike, sports_retailer, 35.00, None, 'High-support sports bra', 'Black, White, Pink, Blue', 'XS,S,M,L,XL', 70, False),
            ('Adidas leggings', womens_clothing, adidas, sports_retailer, 45.00, 35.00, 'Comfortable workout leggings', 'Black, Gray, Pink', 'XS,S,M,L,XL', 65, True),
            
            # Accessories
            ('Ray-Ban Aviator', accessories, rayban, fashion_retailer, 179.00, 149.00, 'Classic aviator sunglasses', 'Gold, Black, Gunmetal', 'One Size', 50, True),
            ('Gucci Belt', accessories, gucci, fashion_retailer, 350.00, None, 'Luxury leather belt', 'Black, Brown', '90,95,100,105,110,115', 25, False),
            
            # Home & Garden
            ('Modern Office Chair', furniture, None, tech_retailer, 299.99, 249.99, 'Ergonomic office chair with lumbar support', 'Black, Gray, White', 'One Size', 30, True),
            ('Coffee Maker Deluxe', kitchen, None, tech_retailer, 89.99, 69.99, 'Programmable coffee maker', 'Black, Silver, Red', 'One Size', 45, True),
            ('Garden Tool Set', garden, None, sports_retailer, 49.99, None, 'Complete garden tool set', 'Multi-color', 'One Size', 60, False),
        ]
        
        for name, category, brand, retailer, price, sale_price, description, colors, sizes, stock, featured in products:
            if not Product.objects.filter(name=name).exists():
                Product.objects.create(
                    name=name,
                    category=category,
                    brand=brand,
                    retailer=retailer,
                    description=description,
                    short_description=description[:100] + '...',
                    price=Decimal(str(price)),
                    sale_price=Decimal(str(sale_price)) if sale_price else None,
                    color=colors,
                    size=sizes,
                    stock=stock,
                    is_featured=featured,
                    is_active=True,
                    tags=', '.join([category.name.lower(), brand.name.lower() if brand else '', 'trendmart', 'quality'])
                )
