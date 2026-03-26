from django.urls import path
from . import views

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

    path('ai/chat/', views.ai_assistant, name='ai_assistant'),

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
]
