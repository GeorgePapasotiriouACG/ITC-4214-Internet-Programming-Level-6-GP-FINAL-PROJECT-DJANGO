# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/sitemaps.py
# Description:  XML sitemap classes for TrendMart using django.contrib.sitemaps.
#               Generates sitemap.xml entries for all active products and
#               categories so Google/Bing can discover and index every page.
#               Registered in eshop/urls.py under /sitemap.xml.
# =============================================================================

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Product, Category


class ProductSitemap(Sitemap):
    """
    Sitemap for all active, approved product detail pages.
    Google uses changefreq and priority hints to decide how often to recrawl.
    Products are updated frequently (price/stock changes) so we use 'weekly'.
    """
    changefreq = 'weekly'   # Suggested recrawl frequency for Google
    priority = 0.8          # High priority — product pages are the core content

    def items(self):
        # Only expose publicly visible products (both flags must be True)
        return Product.objects.filter(is_active=True, is_approved=True)

    def lastmod(self, obj):
        # Tell crawlers when this product was last modified (price/desc changes)
        return obj.updated_at

    def location(self, obj):
        # Returns the URL path for each product (e.g. /products/iphone-15-pro/)
        return obj.get_absolute_url()


class CategorySitemap(Sitemap):
    """
    Sitemap for all active category browse pages.
    Categories change less often than products so we use 'monthly'.
    """
    changefreq = 'monthly'
    priority = 0.6  # Slightly lower than product pages

    def items(self):
        return Category.objects.filter(is_active=True)

    def location(self, obj):
        return obj.get_absolute_url()


class StaticSitemap(Sitemap):
    """
    Sitemap for key static pages: home, product listing, search.
    These never go 'stale' but content changes so we use 'daily'.
    """
    changefreq = 'daily'
    priority = 1.0  # Homepage gets maximum priority

    def items(self):
        # List of named URL patterns to include
        return ['home', 'product_list', 'search']

    def location(self, item):
        return reverse(f'shop:{item}')
