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

import uuid    # Used to auto-generate unique SKU codes for products
import io      # Used for in-memory image buffer during WebP conversion
import os      # Used to rename/replace image file paths after conversion
import secrets  # Used to generate secure share tokens

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
    # Long-term AI preference memory — the AI assistant reads and writes this
    # JSON field to remember the user's favourite brands, size profile, and budget.
    # Example: {"preferred_brands": ["Nike"], "budget_max": 200, "sizes": {"shoes": "42"}}
    ai_preferences = models.JSONField(default=dict, blank=True)
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


# ─── AI Conversation History ───────────────────────────────────────────────────
# Stores persistent, DB-backed AI chat history for authenticated users so that
# conversations survive session expiry and work across multiple devices.
# Anonymous users fall back to the shorter session-based history.
# Each row is a single message (either user or assistant role).

class AIConversation(models.Model):
    """
    Persistent AI chat log for a single user.
    - role='user'      → message sent by the customer
    - role='assistant' → reply generated by OpenRouter/GPT
    Kept in chronological order (ordering = ['created_at']).
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    # FK to Django's built-in User; all messages are deleted when the user account is removed
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_conversations')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    # The raw message content (Markdown is stored as-is)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        # Composite index speeds up "get last N messages for user X" queries
        indexes = [models.Index(fields=['user', 'created_at'])]
        verbose_name = 'AI Conversation Message'
        verbose_name_plural = 'AI Conversation Messages'

    def __str__(self):
        snippet = self.content[:60] + ('…' if len(self.content) > 60 else '')
        return f"{self.user.username} [{self.role}]: {snippet}"


# ─── Loyalty Points ────────────────────────────────────────────────────────────
# Tracks the cumulative loyalty point balance for each user.
# Points are awarded for purchases (1 pt per $1), reviews, referrals, etc.
# Points can be redeemed at checkout for a discount.

class LoyaltyPoints(models.Model):
    """One row per user — total accumulated points and how many have been spent."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='loyalty')
    points = models.PositiveIntegerField(default=0)      # Current redeemable balance
    total_earned = models.PositiveIntegerField(default=0) # Lifetime points earned
    total_spent = models.PositiveIntegerField(default=0)  # Lifetime points redeemed
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.points} pts"

    @classmethod
    def award(cls, user, amount, reason='purchase'):
        """Award `amount` points to a user, creating the record if needed."""
        obj, _ = cls.objects.get_or_create(user=user)
        obj.points += amount
        obj.total_earned += amount
        obj.save()
        LoyaltyTransaction.objects.create(user=user, points=amount, transaction_type='earn', description=reason)
        return obj

    @classmethod
    def redeem(cls, user, amount):
        """Deduct `amount` points. Returns False if balance is insufficient."""
        obj, _ = cls.objects.get_or_create(user=user)
        if obj.points < amount:
            return False
        obj.points -= amount
        obj.total_spent += amount
        obj.save()
        LoyaltyTransaction.objects.create(user=user, points=amount, transaction_type='redeem', description='Redeemed at checkout')
        return True


class LoyaltyTransaction(models.Model):
    """Detailed transaction log so users can see how they earned/spent points."""
    TYPE_CHOICES = [('earn', 'Earned'), ('redeem', 'Redeemed')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loyalty_transactions')
    points = models.IntegerField()  # positive = earned, negative = spent
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} {self.transaction_type} {self.points} pts — {self.description}"


# ─── Notification ─────────────────────────────────────────────────────────────
# Platform-wide notification bell. Covers order updates, price drops, stock
# alerts, AI recommendations, and system announcements.

class Notification(models.Model):
    """One notification row per event per user. Marked is_read when viewed."""
    TYPE_CHOICES = [
        ('order', 'Order Update'),
        ('price_drop', 'Price Drop'),
        ('back_in_stock', 'Back in Stock'),
        ('recommendation', 'Recommendation'),
        ('system', 'System'),
        ('loyalty', 'Loyalty Reward'),
        ('review_reply', 'Review Reply'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    title = models.CharField(max_length=200)
    message = models.TextField()
    # Optional link to the relevant resource (product page, order page, etc.)
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.title}"


# ─── Promo Code ───────────────────────────────────────────────────────────────
# Discount codes that can be applied at checkout. Supports percentage and
# flat-amount discounts. Admins and retailers can create codes.

class PromoCode(models.Model):
    """A reusable or single-use discount code."""
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage (%)'),
        ('flat', 'Flat Amount ($)'),
    ]
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=15, choices=DISCOUNT_TYPES, default='percentage')
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)  # % or $ amount
    # Minimum order total required to use this code
    minimum_order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses = models.PositiveIntegerField(default=0, help_text="0 = unlimited uses")
    times_used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.discount_value}{'%' if self.discount_type == 'percentage' else '$'} off)"

    def is_valid(self):
        """Return True if the code is still active, not expired, and has uses remaining."""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.max_uses > 0 and self.times_used >= self.max_uses:
            return False
        return True

    def calculate_discount(self, order_total):
        """Return the discount amount to subtract from order_total."""
        if not self.is_valid():
            return 0
        if order_total < self.minimum_order:
            return 0
        if self.discount_type == 'percentage':
            return round(order_total * self.discount_value / 100, 2)
        return min(self.discount_value, order_total)


# ─── Search Synonym ───────────────────────────────────────────────────────────
# Maps user search terms to canonical equivalents for better search recall.
# e.g. "sneakers" → "trainers", "mobile" → "phone"

class SearchSynonym(models.Model):
    """A single synonym mapping: searching for `term` also searches `maps_to`."""
    term = models.CharField(max_length=100, unique=True)
    maps_to = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.term} → {self.maps_to}"


# ─── Search Log ───────────────────────────────────────────────────────────────
# Records every search query with its result count. Zero-result queries are
# shown in the admin analytics dashboard to reveal catalogue gaps.

class SearchLog(models.Model):
    """One row per search event. Used to detect zero-result queries."""
    query = models.CharField(max_length=300)
    result_count = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'"{self.query}" → {self.result_count} results'


# ─── Product Q&A ──────────────────────────────────────────────────────────────
# Any logged-in user can ask a question on a product page.
# Retailers and other users can post public answers.

class ProductQuestion(models.Model):
    """A customer question about a specific product."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='questions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_questions')
    question = models.TextField()
    is_approved = models.BooleanField(default=True)  # Admin can hide spam questions
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Q on {self.product.name}: {self.question[:60]}"


class ProductAnswer(models.Model):
    """An answer to a ProductQuestion. Can come from any user or the retailer."""
    question = models.ForeignKey(ProductQuestion, on_delete=models.CASCADE, related_name='answers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_answers')
    answer = models.TextField()
    # True if the answerer is the product's retailer — highlighted in the UI
    is_retailer_answer = models.BooleanField(default=False)
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"A by {self.user.username}: {self.answer[:60]}"


# ─── User Shipping Address ────────────────────────────────────────────────────
# Allows users to save up to 5 shipping addresses for fast checkout.

class UserAddress(models.Model):
    """A saved delivery address for a user (max 5 per user enforced in the view)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=50, default='Home', help_text="e.g. Home, Office")
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Greece')
    postal_code = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.label}: {self.city}"


# ─── Wishlist Share Token ─────────────────────────────────────────────────────
# Generates a secure public URL so users can share their wishlist with others.

class WishlistShareToken(models.Model):
    """A unique, publicly shareable token that exposes a user's wishlist read-only."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist_share')
    token = models.CharField(max_length=64, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-generate a URL-safe 48-character random token on creation
        if not self.token:
            self.token = secrets.token_urlsafe(36)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} wishlist share"


# ─── Stock Notification ───────────────────────────────────────────────────────
# Users can request an email alert when an out-of-stock product is replenished.

class StockNotification(models.Model):
    """Request to be notified when a product comes back into stock."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_notifications')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()  # Stored separately so guest requests work too
    is_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'email')
        ordering = ['-created_at']

    def __str__(self):
        return f"Stock notify: {self.email} for {self.product.name}"


# ─── Newsletter Subscriber ────────────────────────────────────────────────────
# Simple opt-in email list for the weekly deal digest.

class NewsletterSubscriber(models.Model):
    """An email address subscribed to TrendMart's newsletter."""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


# ─── Audit Log ────────────────────────────────────────────────────────────────
# Records significant admin and retailer actions for dispute resolution.

class AuditLog(models.Model):
    """One row per significant action — who did what to which object."""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=200)         # e.g. "Product deleted"
    model_name = models.CharField(max_length=100, blank=True)  # e.g. "Product"
    object_id = models.CharField(max_length=50, blank=True)    # PK of affected object
    detail = models.TextField(blank=True)             # JSON snapshot or description
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} — {self.action} at {self.created_at:%Y-%m-%d %H:%M}"


# ─── Retailer Review Reply ────────────────────────────────────────────────────
# A retailer can post one public reply to a review on their own product.

class ReviewReply(models.Model):
    """Public retailer response to a customer review."""
    review = models.OneToOneField(
        ProductRating, on_delete=models.CASCADE, related_name='retailer_reply'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Should be the retailer
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reply by {self.user.username} on {self.review}"


# ─── Collection / Shop by Mood ────────────────────────────────────────────────
# Curated product collections (e.g. "Summer Essentials", "Gifts under $50").
# Admins create collections; products are tagged into them.

class Collection(models.Model):
    """A hand-curated themed product collection shown on the Shop by Mood page."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, blank=True, help_text="Emoji icon")
    cover_image = models.ImageField(upload_to='collections/', blank=True, null=True)
    products = models.ManyToManyField(Product, related_name='collections', blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            count = 1
            while Collection.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ─── Referral ─────────────────────────────────────────────────────────────────
# Tracks referral links so both the referrer and the new user get bonus points.

class Referral(models.Model):
    """Tracks a referral from one user to a new registered user."""
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    referred = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referral_source')
    # Bonus points awarded — True once each side has been rewarded
    referrer_rewarded = models.BooleanField(default=False)
    referred_rewarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer.username} referred {self.referred.username}"


# ─── A/B Test ─────────────────────────────────────────────────────────────────
# Simple server-side A/B testing framework. Each test has two variants;
# users are assigned deterministically by user_id or session hash.

class ABTest(models.Model):
    """A/B test definition. Variants are 'A' and 'B'."""
    name = models.CharField(max_length=100, unique=True, help_text="e.g. hero_cta_text")
    description = models.TextField(blank=True)
    variant_a = models.TextField(help_text="Content/value for variant A (control)")
    variant_b = models.TextField(help_text="Content/value for variant B (treatment)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_variant(self, user_or_request):
        """Return 'A' or 'B' deterministically based on user/session ID hash."""
        import hashlib
        if hasattr(user_or_request, 'user') and user_or_request.user.is_authenticated:
            key = str(user_or_request.user.id)
        elif hasattr(user_or_request, 'session'):
            key = user_or_request.session.session_key or '0'
        else:
            key = str(user_or_request)
        hash_val = int(hashlib.md5(f"{self.name}{key}".encode()).hexdigest(), 16)
        return 'A' if hash_val % 2 == 0 else 'B'

    def get_value(self, user_or_request):
        """Return the actual value (text/URL/etc.) for the assigned variant."""
        return self.variant_a if self.get_variant(user_or_request) == 'A' else self.variant_b

    def __str__(self):
        return self.name


# ─── Trending Score ───────────────────────────────────────────────────────────
# Pre-computed trend score per product, updated by a management command.
# Combines views, recent purchases, ratings, and wishlist adds into one number.

class ProductTrendScore(models.Model):
    """Cached trending score for a product, recalculated by the update_trends command."""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='trend_score')
    score = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-score']

    def __str__(self):
        return f"{self.product.name}: {self.score:.2f}"
