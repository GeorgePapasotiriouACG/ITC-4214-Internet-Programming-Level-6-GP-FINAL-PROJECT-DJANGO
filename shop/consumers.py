# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/consumers.py
# Description:  Django Channels WebSocket consumers for TrendMart's real-time
#               features. Provides a StockConsumer that clients connect to for
#               a specific product and receives live stock level updates.
#
#               Stock warnings are pushed from views (e.g. add_to_cart) via
#               channel groups. The frontend JS on the product detail page
#               connects to ws://<host>/ws/stock/<slug>/ and displays an
#               inline "Only X left!" banner when stock is low.
#
#               REQUIREMENTS: pip install channels channels-redis
#               Then enable channels in settings.py (see commented config).
#
# Usage (from a view or signal):
#   from channels.layers import get_channel_layer
#   from asgiref.sync import async_to_sync
#   channel_layer = get_channel_layer()
#   async_to_sync(channel_layer.group_send)(
#       f'stock_{product_slug}',
#       {'type': 'stock_update', 'stock': product.stock, 'slug': product.slug}
#   )
# =============================================================================

import json

try:
    from channels.generic.websocket import AsyncWebsocketConsumer

    class StockConsumer(AsyncWebsocketConsumer):
        """
        WebSocket consumer that pushes real-time stock updates to product
        detail page visitors. Each product gets its own channel group
        named "stock_<slug>" so broadcasts are product-specific.
        """

        async def connect(self):
            """
            Called when a client opens a WebSocket connection.
            Join the channel group for the requested product slug.
            """
            self.slug = self.scope['url_route']['kwargs']['slug']
            # Group name pattern: stock_iphone-15-pro (slug with dashes)
            self.group_name = f"stock_{self.slug}"

            # Join the product-specific group so we receive stock broadcasts
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            # Immediately send current stock level to the newly connected client
            try:
                from shop.models import Product
                from asgiref.sync import sync_to_async

                product = await sync_to_async(
                    lambda: Product.objects.filter(slug=self.slug, is_active=True).first()
                )()
                if product:
                    await self.send(text_data=json.dumps({
                        'type': 'stock_update',
                        'stock': product.stock,
                        'slug': self.slug,
                    }))
            except Exception:
                pass  # DB errors on connect are non-fatal

        async def disconnect(self, close_code):
            """
            Called when the WebSocket closes. Leave the channel group cleanly.
            """
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        async def receive(self, text_data):
            """
            The client doesn't need to send any data — this is push-only.
            Silently ignore any messages from the client side.
            """
            pass

        async def stock_update(self, event):
            """
            Handler called when a stock_update message is sent to our group.
            Forwards the payload to the connected WebSocket client.
            Triggered by: async_to_sync(channel_layer.group_send)(group_name, event)
            """
            await self.send(text_data=json.dumps({
                'type': 'stock_update',
                'stock': event['stock'],
                'slug': event['slug'],
            }))

except ImportError:
    # Django Channels not installed — define a stub so imports don't break
    class StockConsumer:  # type: ignore
        """Stub consumer — install channels to enable WebSocket stock updates."""
        pass
