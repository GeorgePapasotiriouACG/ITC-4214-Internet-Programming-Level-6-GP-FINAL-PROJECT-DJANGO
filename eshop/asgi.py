# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         eshop/asgi.py
# Description:  ASGI entry point for TrendMart. Supports both standard HTTP
#               (via Django's WSGI-compatible ASGI app) and WebSockets (via
#               Django Channels). WebSocket connections are routed to the
#               shop.consumers module for real-time features such as:
#                 - Live stock warnings ("Only 2 left!")
#                 - Order status push notifications
#
#               REQUIREMENTS:
#                 pip install channels channels-redis
#               Also add 'channels' to INSTALLED_APPS and set ASGI_APPLICATION
#               and CHANNEL_LAYERS in settings.py (see commented config there).
#
#               Without Channels installed, the file falls back to standard
#               Django ASGI so HTTP functionality is never broken.
# =============================================================================

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eshop.settings')

# ── Try to boot Django Channels ───────────────────────────────
# If channels is not installed this gracefully degrades to plain HTTP ASGI.
try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from django.urls import path
    from shop.consumers import StockConsumer  # WebSocket consumer

    django_asgi_app = get_asgi_application()

    application = ProtocolTypeRouter({
        # Standard HTTP requests are handled by Django as normal
        'http': django_asgi_app,

        # WebSocket connections are routed to our StockConsumer
        # URL: ws://<host>/ws/stock/<product_slug>/
        'websocket': AuthMiddlewareStack(
            URLRouter([
                path('ws/stock/<slug:slug>/', StockConsumer.as_asgi()),
            ])
        ),
    })

except ImportError:
    # Django Channels not installed — serve HTTP only (no WebSockets)
    application = get_asgi_application()
