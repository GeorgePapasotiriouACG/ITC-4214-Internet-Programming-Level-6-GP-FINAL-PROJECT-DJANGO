# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         eshop/urls.py
# Description:  Root URL configuration for TrendMart. Wires together:
#               - Django's built-in admin at /django-admin/
#               - The shop app (all storefront URLs) at /
#               - XML sitemap at /sitemap.xml (SEO — Google/Bing indexing)
#               - robots.txt at /robots.txt (crawler instruction file)
#               - Media file serving in development (handled by WhiteNoise/CDN in prod)
# =============================================================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

# Import TrendMart's sitemap classes
from shop.sitemaps import ProductSitemap, CategorySitemap, StaticSitemap

# Registry of all sitemap sections — each key becomes a <url> group in the XML
sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
    'static': StaticSitemap,
}

urlpatterns = [
    # Django's built-in admin interface (superuser only)
    path('django-admin/', admin.site.urls),

    # Sitemap XML — submitted to Google Search Console for SEO indexing
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    # robots.txt — tells crawlers what to index and what to skip
    # Template lives at templates/robots.txt
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),

    # All TrendMart shop URLs (products, auth, cart, AI, admin panel, etc.)
    path('', include('shop.urls')),

# In development, Django serves uploaded media files (product images, avatars).
# In production, replace this with a CDN (Cloudflare/CloudFront) or WhiteNoise.
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
