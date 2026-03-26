from django.urls import path
from . import views

app_name = "shop"

urlpatterns = [
    path("", views.home, name="home"),
    path("category/<int:category_id>/", views.category_products, name="category_products"),
    path("order/", views.place_order, name="place_order"),
    path("order/success/", views.order_success, name="order_success"),
]