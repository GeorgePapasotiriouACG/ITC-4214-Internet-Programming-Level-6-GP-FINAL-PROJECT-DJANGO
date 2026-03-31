# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/urls.py
# Description:  URL routing for the TrendMart shop application. Maps every
#               URL pattern to its corresponding view function. Organised into
#               logical sections: catalogue, auth, dashboard, cart, orders,
#               wishlist, ratings, AI assistant, and admin panel.
# =============================================================================

from django.urls import path
from . import views

# All URLs in this file are namespaced as 'shop' (referenced as 'shop:view_name')
app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('category/<slug:slug>/', views.category_view, name='category'),
    path('search/', views.search_view, name='search'),
    path('search/autocomplete/', views.search_autocomplete, name='search_autocomplete'),

    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/retailer/', views.retailer_dashboard, name='retailer_dashboard'),
    path('dashboard/retailer/product/<int:pk>/edit/', views.retailer_edit_product, name='retailer_edit_product'),
    path('dashboard/retailer/product/<int:pk>/delete/', views.retailer_delete_product, name='retailer_delete_product'),

    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),

    path('checkout/', views.checkout, name='checkout'),
    path('order/success/<str:order_number>/', views.order_success, name='order_success'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),

    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/', views.toggle_wishlist, name='toggle_wishlist'),

    path('rate/<slug:slug>/', views.rate_product, name='rate_product'),
    path('review/<int:review_id>/helpful/', views.mark_review_helpful, name='mark_review_helpful'),

    path('ai/chat/', views.ai_assistant, name='ai_assistant'),
    path('ai/stream/', views.ai_stream, name='ai_stream'),
    path('ai/search/', views.ai_search, name='ai_search'),

    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/products/', views.admin_products, name='admin_products'),
    path('admin-panel/products/<int:pk>/edit/', views.admin_product_edit, name='admin_product_edit'),
    path('admin-panel/products/<int:pk>/delete/', views.admin_product_delete, name='admin_product_delete'),
    path('admin-panel/products/<int:pk>/approve/', views.admin_product_approve, name='admin_product_approve'),
    path('admin-panel/categories/', views.admin_categories, name='admin_categories'),
    path('admin-panel/categories/<int:pk>/delete/', views.admin_category_delete, name='admin_category_delete'),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/retailers/<int:user_id>/approve/', views.admin_approve_retailer, name='admin_approve_retailer'),
    path('admin-panel/orders/', views.admin_orders, name='admin_orders'),
    path('admin-panel/orders/<str:order_number>/status/', views.admin_order_status, name='admin_order_status'),
    path('admin-panel/search-logs/', views.admin_search_logs, name='admin_search_logs'),
    path('admin-panel/audit-log/', views.admin_audit_log, name='admin_audit_log'),
    path('admin-panel/product-performance/', views.admin_product_performance, name='admin_product_performance'),

    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/count/', views.notifications_count, name='notifications_count'),

    path('loyalty/', views.loyalty_dashboard, name='loyalty_dashboard'),
    path('referral/', views.referral_dashboard, name='referral_dashboard'),

    path('addresses/', views.address_list, name='address_list'),
    path('addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),

    path('cart/promo/', views.apply_promo_code, name='apply_promo_code'),
    path('cart/save-for-later/<int:item_id>/', views.save_for_later, name='save_for_later'),
    path('cart/mini/', views.mini_cart_data, name='mini_cart_data'),

    path('store/<str:username>/', views.retailer_storefront, name='retailer_storefront'),
    path('dashboard/retailer/analytics/', views.retailer_analytics, name='retailer_analytics'),
    path('dashboard/retailer/import/', views.retailer_csv_import, name='retailer_csv_import'),
    path('dashboard/retailer/ai-description/', views.ai_generate_description, name='ai_generate_description'),

    path('products/<slug:slug>/ask/', views.ask_question, name='ask_question'),
    path('products/<slug:slug>/stock-notify/', views.notify_back_in_stock, name='notify_back_in_stock'),
    path('questions/<int:question_id>/answer/', views.answer_question, name='answer_question'),
    path('reviews/<int:review_id>/reply/', views.reply_to_review, name='reply_to_review'),

    path('wishlist/share/', views.generate_wishlist_share, name='generate_wishlist_share'),
    path('wishlist/shared/<str:token>/', views.shared_wishlist, name='shared_wishlist'),

    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),

    path('collections/', views.collections_list, name='collections'),
    path('collections/<slug:slug>/', views.collection_detail, name='collection_detail'),

    path('spin/', views.spin_wheel, name='spin_wheel'),
    path('surprise/', views.surprise_me, name='surprise_me'),

    path('account/delete/', views.delete_account, name='delete_account'),
    path('account/2fa/setup/', views.setup_2fa, name='setup_2fa'),
    path('account/2fa/disable/', views.disable_2fa, name='disable_2fa'),
    path('account/2fa/verify/', views.verify_2fa, name='verify_2fa'),

    path('faq/', views.faq_view, name='faq'),
    path('settings/dark-mode/', views.toggle_dark_mode, name='toggle_dark_mode'),

    # Health check — used by load balancers, Docker, Kubernetes, and hosting
    # platforms (Render, Railway, Heroku) to verify the app is alive.
    # Returns JSON {"status": "ok"} with HTTP 200, or {"status": "error"} with 503.
    path('health/', views.health_check, name='health_check'),

    # AI Review Summarisation — generates a 2-3 sentence AI summary of a product's reviews
    path('products/<slug:slug>/summarise-reviews/', views.ai_summarise_reviews, name='ai_summarise_reviews'),

    # Quick View JSON API — returns rich product data for the quick-view modal
    path('api/products/<slug:slug>/quickview/', views.product_quickview_api, name='product_quickview_api'),

    # Static policy & support pages
    path('shipping-policy/', views.shipping_policy, name='shipping_policy'),
    path('returns-refunds/', views.returns_refunds, name='returns_refunds'),
    path('contact-support/', views.contact_support, name='contact_support'),

    # Web Push Notifications
    path('push/vapid-key/', views.push_vapid_public_key, name='push_vapid_key'),
    path('push/subscribe/', views.push_subscribe, name='push_subscribe'),
    path('push/unsubscribe/', views.push_unsubscribe, name='push_unsubscribe'),
]
