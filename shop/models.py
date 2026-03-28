import uuid
# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/models.py
# Description:  All database models for TrendMart. Covers user roles,
#               product catalogue (with variants and images), categories,
#               brands, shopping cart, orders, wishlists, ratings/reviews,
#               browsing history, and retailer profiles.
# =============================================================================

import uuid  # Used to auto-generate unique SKU codes for products
import io    # Used for in-memory image buffer during WebP conversion
import os    # Used to rename/replace image file paths after conversion

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.base import ContentFile  # Wraps raw bytes as a Django file


# ── WebP conversion helper ─────────────────────────────────────────────────────
# Converts any uploaded image (JPEG, PNG, BMP, etc.) to WebP format using
# Pillow. WebP is ~25-35% smaller than JPEG at equivalent quality, which means
# faster page loads and lower storage costs.
# Returns True if conversion succeeded; False if Pillow is not installed or
# the image field is empty (so callers can safely skip).

def _convert_image_to_webp(image_field, quality=85):
    """
    Convert an ImageField's file to WebP in-place.
    Called from model.save() before the super() call persists the record.
    quality: 1-100 (85 is the sweet-spot — great quality, small file).
    """
    try:
        from PIL import Image as PILImage
    except ImportError:
        # Pillow not installed — skip silently so the app still works
        return False

    from django.conf import settings
    if not getattr(settings, 'WEBP_CONVERSION_ENABLED', True):
        return False

    if not image_field or not image_field.name:
        return False

    try:
        image_field.open('rb')
        pil_img = PILImage.open(image_field)
        pil_img = pil_img.convert('RGBA' if pil_img.mode in ('RGBA', 'P') else 'RGB')

        buffer = io.BytesIO()
        pil_img.save(buffer, format='WEBP', quality=quality, method=6)
        buffer.seek(0)

        # Build the new .webp filename (replace whatever extension was used)
        original_name = os.path.splitext(image_field.name)[0]
        new_name = original_name.split('/')[-1] + '.webp'

        image_field.save(new_name, ContentFile(buffer.read()), save=False)
        return True
    except Exception:
        # Conversion failed (corrupt image, wrong mode, etc.) — keep original
        return False


# ─── User Profile ─────────────────────────────────────────────────────────────
# Extends Django's built-in User model with TrendMart-specific fields.
# Every registered user gets exactly one UserProfile via a OneToOne relation.

class UserProfile(models.Model):
    # Three platform roles determine what each user can access
    ROLE_CHOICES = [
        ('customer', 'Customer'),    # Default — can browse, purchase, review
        ('retailer', 'Retailer'),    # Can list & manage their own products
        ('admin', 'Administrator'),  # Full platform control (mirrors is_staff)
    ]
    # Link back to Django's built-in User; deleting the user cascades here
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    # Optional profile picture stored under media/avatars/
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def is_retailer(self):
        """Return True if this user is a retailer (can manage their own products)."""
        return self.role == 'retailer'

    def is_admin_role(self):
        """Return True for admin-role users OR Django staff (is_staff covers superusers)."""
        return self.role == 'admin' or self.user.is_staff


# ─── Retailer Profile ─────────────────────────────────────────────────────────
# Extra business information for users with the 'retailer' role.
# An admin must approve the retailer before their products go live.

class RetailerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='retailer_profile')
    business_name = models.CharField(max_length=200)
    business_description = models.TextField(blank=True)
    business_address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    # Admin must set this to True before the retailer can sell
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name


# ─── Category ─────────────────────────────────────────────────────────────────
# Supports unlimited parent/child nesting (e.g. Electronics > Smartphones).
# A null parent means it's a top-level (root) category shown in navigation.

class Category(models.Model):
    name = models.CharField(max_length=200)
    # URL-friendly identifier auto-generated from the name on first save
    slug = models.SlugField(unique=True, blank=True)
    # Self-referential FK: null = root category, set = subcategory
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='children'
    )
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, blank=True, help_text="Emoji or CSS icon class")
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    # Controls display order in navigation menus
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        # Auto-generate a unique slug from the name if not already set.
        # Appends a numeric suffix if the base slug already exists (e.g. "shoes-2").
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            count = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        # Show "Parent > Child" for subcategories to make admin readable
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('shop:category', kwargs={'slug': self.slug})


# ─── Brand ────────────────────────────────────────────────────────────────────
# Represents a product brand (e.g. Apple, Nike). Products can be optionally
# linked to a brand for filtering and brand-search functionality.

class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Same slug-generation logic as Category — ensures URL uniqueness
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            count = 1
            while Brand.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ─── Product ──────────────────────────────────────────────────────────────────
# Core catalogue item. Each product belongs to one category and optionally a
# brand. It may be owned by a retailer (null = platform/admin product).
# Products are visible only when both is_active=True AND is_approved=True.

class Product(models.Model):
    # Relationships — cascade delete from category; brand kept even if brand deleted
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL, related_name='products')
    # retailer=null means the product was added by an admin / the platform itself
    retailer = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='retailer_products'
    )
    name = models.CharField(max_length=200)
    # SEO-friendly URL slug, auto-generated from name on first save
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    # Short teaser shown on product cards and search results
    short_description = models.CharField(max_length=300, blank=True)
    # Base price (always required); sale_price overrides it when set
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Primary product image; additional gallery images use ProductImage model
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    # Simple color/size text fields (used when ProductVariant rows are not needed)
    color = models.CharField(max_length=50, blank=True)
    size = models.CharField(max_length=200, blank=True, help_text="Comma-separated sizes, e.g. S,M,L,XL")
    stock = models.PositiveIntegerField(default=0)
    # is_featured = shown in hero / featured sections on the homepage
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    # is_approved: retailer products start unapproved until an admin approves them
    is_approved = models.BooleanField(default=True)
    # Comma-separated search keywords used by the recommender and tag search
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    # Unique product identifier, auto-generated from UUID on first save
    sku = models.CharField(max_length=100, unique=True, blank=True)
    # Incremented every time the product detail page is loaded (used for popularity ranking)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Newest products appear first by default in all querysets
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Auto-generate a collision-safe slug from the product name
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            count = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            self.slug = slug
        # Auto-generate a 12-char uppercase SKU from a random UUID
        if not self.sku:
            self.sku = str(uuid.uuid4()).upper()[:12]
        # Convert the primary product image to WebP before saving to storage.
        # This reduces image sizes by 25-35% vs JPEG with no visible quality loss.
        # Only runs when a new image file has been provided (image._file is not None).
        if self.image and hasattr(self.image, '_file') and self.image._file is not None:
            _convert_image_to_webp(self.image)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_effective_price(self):
        """Return the currently active selling price (sale_price if set, else price)."""
        return self.sale_price if self.sale_price else self.price

    def is_on_sale(self):
        """Return True only when a sale_price is set AND it's actually lower than regular price."""
        return self.sale_price is not None and self.sale_price < self.price

    def get_discount_percentage(self):
        """Calculate and return the % discount rounded to the nearest integer."""
        if self.is_on_sale():
            return int(((self.price - self.sale_price) / self.price) * 100)
        return 0

    def get_avg_rating(self):
        """Compute the mean star rating from all reviews. Returns 0 if no reviews yet."""
        ratings = self.ratings.all()
        if ratings.exists():
            return round(sum(r.rating for r in ratings) / ratings.count(), 1)
        return 0

    def get_rating_count(self):
        """Return the total number of submitted reviews for this product."""
        return self.ratings.count()

    def get_tags_list(self):
        """Split the comma-separated tags string into a clean Python list."""
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()]
        return []

    def get_sizes_list(self):
        """Split the comma-separated size string into a clean Python list."""
        if self.size:
            return [s.strip() for s in self.size.split(',') if s.strip()]
        return []

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('shop:product_detail', kwargs={'slug': self.slug})

    def is_in_stock(self):
        """Return True if at least one unit is available in the main stock field."""
        return self.stock > 0


# ─── Product Variant ──────────────────────────────────────────────────────────
# Allows a single product to have multiple purchasable options (e.g. a shirt in
# S/M/L/XL or a phone in 128GB/256GB) each with its own stock and price modifier.
# The product detail page renders size buttons and colour swatches from these rows.

class ProductVariant(models.Model):
    # Deleting the parent product removes all its variants too
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    # Either size or color (or both) should be set; leaving both blank is valid too
    size = models.CharField(max_length=50, blank=True, help_text="e.g. S, M, L, XL, 42, 256GB")
    color = models.CharField(max_length=50, blank=True, help_text="e.g. Red, Blue, Black")
    # Hex colour used to render the colour swatch dot on the product page
    color_hex = models.CharField(max_length=7, blank=True, help_text="Hex code e.g. #FF0000")
    # Delta applied to the product's base price — can be negative for cheaper options
    price_modifier = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Amount added to/subtracted from base price. e.g. 50 means +$50"
    )
    stock = models.PositiveIntegerField(default=0)
    # Optional suffix appended to the parent SKU to create variant-level identifiers
    sku_suffix = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        # Order variants by size first, then colour, for predictable UI ordering
        ordering = ['size', 'color']

    def __str__(self):
        parts = []
        if self.size:
            parts.append(self.size)
        if self.color:
            parts.append(self.color)
        return f"{self.product.name} — {' / '.join(parts)}" if parts else self.product.name

    def get_price(self):
        """Return the final price for this variant (base product price + modifier), floored at 0."""
        base = self.product.get_effective_price()
        return max(base + self.price_modifier, 0)

    def is_in_stock(self):
        """Return True if this specific variant has at least one unit available."""
        return self.stock > 0


# ─── Product Image ────────────────────────────────────────────────────────────
# Stores additional gallery images for a product beyond its primary `image` field.
# Rendered as thumbnail strip on the product detail page.

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']


# ─── Product Rating ───────────────────────────────────────────────────────────
# One review per user per product (enforced by unique_together).
# Only logged-in users can submit reviews; verified_purchase is auto-set when
# the user has an order containing that product.

class ProductRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    # 1–5 star rating validated both by choices and view-level checks
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    review = models.TextField(blank=True)
    # Optional photo uploaded alongside the review (stored under media/review_photos/)
    review_photo = models.ImageField(upload_to='review_photos/', blank=True, null=True)
    # Auto-set when the reviewer has a completed order containing this product
    is_verified_purchase = models.BooleanField(default=False)
    # Incremented via AJAX when other logged-in users click "Helpful"
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Prevent duplicate reviews — one review per (user, product) pair
        unique_together = ('product', 'user')
        # Show newest reviews first
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating}star"


# ─── Wishlist ─────────────────────────────────────────────────────────────────
# Simple many-to-many relationship between a user and saved products.
# Toggled via AJAX — adding again removes the item (toggle behaviour).

class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure the same product can't be saved twice in a user's wishlist
        unique_together = ('user', 'product')
        ordering = ['-added_at']


# ─── Viewed Product ───────────────────────────────────────────────────────────
# Records which products a user (or anonymous session) has viewed.
# Used by the recommender system and the personalized dashboard.

class ViewedProduct(models.Model):
    # Supports both logged-in users and anonymous visitors (tracked by session)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name='viewed_products'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='views')
    # Django session key used to track anonymous visitors across page loads
    session_key = models.CharField(max_length=100, blank=True)
    # auto_now=True means this timestamp is refreshed on every re-visit
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']


# ─── Shopping Cart ────────────────────────────────────────────────────────────
# Persistent cart stored in the database (not session-only), supporting both
# logged-in users (identified by user FK) and guests (identified by session key).
# On login, the guest cart is merged into the user's cart.

class Cart(models.Model):
    # If null, this is a guest cart identified by session_key instead
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name='cart'
    )
    # Django session key for anonymous (guest) carts
    session_key = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_total(self):
        """Sum the subtotal of every line item in this cart."""
        return sum(item.get_subtotal() for item in self.items.all())

    def get_item_count(self):
        """Return the total number of individual units across all cart lines."""
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        return f"Cart ({self.user.username if self.user else self.session_key[:8]})"


# ─── Cart Item ────────────────────────────────────────────────────────────────
# One line in the shopping cart. Stores the chosen product, quantity, and size.

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    # The size selected by the user (empty string if not applicable)
    size = models.CharField(max_length=20, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def get_subtotal(self):
        """Return the line total: effective product price × quantity."""
        return self.product.get_effective_price() * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"


# ─── Order ────────────────────────────────────────────────────────────────────
# Simulated order created at checkout. No real payment processing — serves as a
# purchase record for order history, status tracking, and verified-purchase flags.

class Order(models.Model):
    # Five-stage lifecycle from placement to delivery (or cancellation)
    STATUS_CHOICES = [
        ('pending', 'Pending'),         # Just placed, awaiting processing
        ('processing', 'Processing'),   # Being prepared / packed
        ('shipped', 'Shipped'),         # Dispatched to courier
        ('delivered', 'Delivered'),     # Received by the customer
        ('cancelled', 'Cancelled'),     # Cancelled by user or admin
    ]
    # SET_NULL so orders survive if a user account is deleted
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # Shipping / contact details captured at checkout (snapshot in time)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    # Snapshot of the grand total at checkout time (prices may change later)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Human-readable order reference auto-generated in save() (e.g. TM-2026-XXXX)
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"TM{str(uuid.uuid4()).upper()[:8]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=20, blank=True)

    def get_subtotal(self):
        return self.product_price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"
