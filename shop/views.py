from django.shortcuts import render, get_object_or_404, redirect
from .models import Category, Product, Order

def home(request):
    categories = Category.objects.all()
    products = Product.objects.all().order_by('-created_at')  # newest first
    return render(request, "shop/home.html", {"categories": categories, "products": products})

def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category).order_by('-created_at')
    categories = Category.objects.all()
    return render(request, "shop/home.html", {"categories": categories, "products": products, "selected_category": category})

def place_order(request):
    if request.method == "POST":
        name = request.POST["name"]
        email = request.POST["email"]
        address = request.POST["address"]
        product_ids = request.POST.getlist("products")
        order = Order.objects.create(name=name, email=email, address=address)
        order.products.set(product_ids)
        return redirect("shop:order_success")
    products = Product.objects.all()
    return render(request, "shop/order.html", {"products": products})

def order_success(request):
    return render(request, "shop/order_success.html")

