from django.contrib import admin
# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/admin.py
# Description:  Django Admin configuration for TrendMart. Registers all models
#               with custom list displays, filters, search, inline editors,
#               and bulk actions. Admins manage all catalogue data here;
#               retailers are limited to their own products via queryset overrides.
# =============================================================================

from .models import (
    UserProfile, RetailerProfile, Category, Brand, Product,
    ProductImage, ProductVariant, ProductRating, WishlistItem, ViewedProduct,
    Cart, CartItem, Order, OrderItem
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'city', 'country', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'phone')


@admin.register(RetailerProfile)
class RetailerProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('business_name', 'user__username')
    actions = ['approve_retailers']

    def approve_retailers(self, request, queryset):
        queryset.update(is_approved=True)
    approve_retailers.short_description = "Approve selected retailers"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug', 'is_active', 'order')
    list_filter = ('is_active', 'parent')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 2


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 3
    fields = ('size', 'color', 'color_hex', 'price_modifier', 'stock', 'sku_suffix', 'is_active')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'color', 'get_price', 'stock', 'is_active')
    list_filter = ('is_active', 'color')
    search_fields = ('product__name', 'size', 'color', 'sku_suffix')

    def get_price(self, obj):
        return f"${obj.get_price():.2f}"
    get_price.short_description = 'Price'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'price', 'sale_price', 'stock', 'is_active', 'is_approved', 'is_featured', 'created_at')
    list_filter = ('is_active', 'is_approved', 'is_featured', 'category', 'brand')
    search_fields = ('name', 'description', 'sku', 'tags')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]
    actions = ['approve_products', 'feature_products', 'unfeature_products']

    def approve_products(self, request, queryset):
        queryset.update(is_approved=True)
    approve_products.short_description = "Approve selected products"

    def feature_products(self, request, queryset):
        queryset.update(is_featured=True)
    feature_products.short_description = "Mark as featured"

    def unfeature_products(self, request, queryset):
        queryset.update(is_featured=False)
    unfeature_products.short_description = "Remove from featured"


@admin.register(ProductRating)
class ProductRatingAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_verified_purchase', 'created_at')
    list_filter = ('rating', 'is_verified_purchase')
    search_fields = ('product__name', 'user__username', 'review')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key', 'created_at')
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'product_price', 'quantity', 'size')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'full_name', 'status', 'total_amount', 'created_at')
    list_filter = ('status',)
    search_fields = ('order_number', 'full_name', 'email')
    inlines = [OrderItemInline]
    readonly_fields = ('order_number', 'total_amount')
