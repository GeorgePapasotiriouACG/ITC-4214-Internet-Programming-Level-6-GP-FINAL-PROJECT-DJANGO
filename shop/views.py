import json
# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/views.py
# Description:  All Django view functions for TrendMart. Covers home page,
#               product listing/search/filtering, product detail, user auth
#               (register/login/logout/profile), shopping cart, checkout,
#               orders, wishlist, AJAX ratings, AI assistant chatbot,
#               recommender system, retailer dashboard, and admin panel.
# =============================================================================

from functools import wraps  # Preserves decorated function's __name__ and docstring

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import models as django_models
from django.db.models import Q, Avg, Count, F, Sum
from django.core.paginator import Paginator
from django.utils import timezone

# Import all models from the shop app
from .models import (
    Category, Product, Brand, ProductRating, WishlistItem,
    ViewedProduct, Cart, CartItem, Order, OrderItem, UserProfile,
    RetailerProfile, ProductVariant
)
# Import all forms from the shop app
from .forms import (
    CustomerRegistrationForm, RetailerRegistrationForm, UserProfileForm,
    ProductRatingForm, ProductForm, CategoryForm, BrandForm, CheckoutForm
)


# ─── Access Control Decorators ────────────────────────────────────────────────
# These decorators wrap views and enforce role-based access control (RBAC).
# They redirect unauthorised users rather than returning 403 responses, which
# provides a better UX and prevents information leakage.

def admin_required(view_func):
    """
    Decorator that restricts a view to admin users only.
    Accepts Django staff (is_staff=True) OR users with profile.role='admin'.
    All others are redirected to the home page with an error message.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # Redirect unauthenticated visitors to login
            messages.error(request, "Please log in to continue.")
            return redirect('shop:login')
        # Django superusers and staff always pass
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        try:
            # Also accept users whose UserProfile.role is explicitly 'admin'
            if request.user.profile.role == 'admin':
                return view_func(request, *args, **kwargs)
        except UserProfile.DoesNotExist:
            pass
        messages.error(request, "Admin access required.")
        return redirect('shop:home')
    return wrapper


def retailer_required(view_func):
    """
    Decorator that restricts a view to retailer or admin users.
    Redirects regular customers and unauthenticated visitors.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('shop:login')
        try:
            profile = request.user.profile
            # Both retailers AND admins can access retailer views
            if profile.role in ('retailer', 'admin') or request.user.is_staff:
                return view_func(request, *args, **kwargs)
        except UserProfile.DoesNotExist:
            pass
        messages.error(request, "Retailer access required.")
        return redirect('shop:home')
    return wrapper


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user, defaults={'session_key': ''})
        return cart
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart


def get_recommendations(user, limit=6):
    from django.db.models import Count
    viewed_ids = ViewedProduct.objects.filter(user=user).values_list('product_id', flat=True)
    if not viewed_ids:
        return Product.objects.filter(is_active=True, is_approved=True).order_by('-views_count')[:limit]
    viewed_cats = Product.objects.filter(id__in=viewed_ids).values_list('category_id', flat=True)
    recs = Product.objects.filter(
        is_active=True, is_approved=True, category_id__in=viewed_cats
    ).exclude(id__in=viewed_ids).order_by('-views_count')[:limit]
    if recs.count() < limit:
        extras = Product.objects.filter(
            is_active=True, is_approved=True
        ).exclude(id__in=list(viewed_ids) + list(recs.values_list('id', flat=True))
        ).order_by('-views_count')[:limit - recs.count()]
        recs = list(recs) + list(extras)
    return recs


def track_view(request, product):
    product.views_count += 1
    product.save(update_fields=['views_count'])
    if request.user.is_authenticated:
        ViewedProduct.objects.update_or_create(
            user=request.user, product=product,
            defaults={'viewed_at': timezone.now()}
        )
    else:
        if not request.session.session_key:
            request.session.create()
        ViewedProduct.objects.update_or_create(
            session_key=request.session.session_key, product=product, user=None,
            defaults={'viewed_at': timezone.now()}
        )


# ─── Home & Catalogue ─────────────────────────────────────────────────────────

def home(request):
    featured = Product.objects.filter(is_active=True, is_approved=True, is_featured=True)[:8]
    new_arrivals = Product.objects.filter(is_active=True, is_approved=True).order_by('-created_at')[:8]
    root_categories = Category.objects.filter(parent=None, is_active=True)
    best_sellers = Product.objects.filter(
        is_active=True, is_approved=True
    ).annotate(order_count=Count('orderitem')).order_by('-order_count')[:8]
    recommendations = []
    if request.user.is_authenticated:
        recommendations = get_recommendations(request.user, limit=6)
    context = {
        'featured': featured,
        'new_arrivals': new_arrivals,
        'root_categories': root_categories,
        'best_sellers': best_sellers,
        'recommendations': recommendations,
    }
    return render(request, 'shop/home.html', context)


def product_list(request):
    products = Product.objects.filter(is_active=True, is_approved=True).select_related('brand', 'category')
    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)

    category_slug = request.GET.get('category', '')
    brand_slug = request.GET.get('brand', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    color = request.GET.get('color', '')
    size = request.GET.get('size', '')
    sort = request.GET.get('sort', 'newest')
    query = request.GET.get('q', '').strip()
    selected_category = None

    if category_slug:
        try:
            selected_category = Category.objects.get(slug=category_slug)
            cat_ids = [selected_category.id] + list(
                selected_category.children.values_list('id', flat=True)
            )
            products = products.filter(category_id__in=cat_ids)
        except Category.DoesNotExist:
            pass

    if brand_slug:
        products = products.filter(brand__slug=brand_slug)

    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass

    if color:
        products = products.filter(color__icontains=color)

    if size:
        products = products.filter(size__icontains=size)

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query) |
            Q(brand__name__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()

    sort_map = {
        'newest': '-created_at',
        'price_asc': 'price',
        'price_desc': '-price',
        'popular': '-views_count',
    }
    products = products.order_by(sort_map.get(sort, '-created_at'))

    all_colors = list(filter(None, Product.objects.filter(is_active=True).values_list('color', flat=True).distinct()))

    paginator = Paginator(products, 12)
    page = paginator.get_page(request.GET.get('page', 1))

    context = {
        'products': page,
        'categories': categories,
        'brands': brands,
        'all_colors': all_colors,
        'query': query,
        'selected_category': selected_category,
        'selected_category_slug': category_slug,
        'selected_brand': brand_slug,
        'min_price': min_price,
        'max_price': max_price,
        'selected_color': color,
        'selected_size': size,
        'sort': sort,
        'total_count': paginator.count,
    }
    return render(request, 'shop/product_list.html', context)


def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    request.GET = request.GET.copy()
    request.GET['category'] = slug
    return product_list(request)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True, is_approved=True)
    track_view(request, product)

    related = Product.objects.filter(
        category=product.category, is_active=True, is_approved=True
    ).exclude(id=product.id)[:4]

    tag_recs = Product.objects.filter(is_active=True, is_approved=True).exclude(id=product.id)
    if product.tags:
        tag_q = Q()
        for tag in product.get_tags_list():
            tag_q |= Q(tags__icontains=tag)
        tag_recs = tag_recs.filter(tag_q)
    elif product.brand:
        tag_recs = tag_recs.filter(brand=product.brand)
    tag_recs = tag_recs[:4]

    user_rating = None
    rating_form = ProductRatingForm()
    if request.user.is_authenticated:
        try:
            user_rating = ProductRating.objects.get(product=product, user=request.user)
            rating_form = ProductRatingForm(instance=user_rating)
        except ProductRating.DoesNotExist:
            pass

    ratings = product.ratings.select_related('user').all()
    rating_dist = {i: 0 for i in range(1, 6)}
    for r in ratings:
        rating_dist[r.rating] += 1

    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = WishlistItem.objects.filter(user=request.user, product=product).exists()

    from .templatetags.shop_tags import product_image
    product_img_url = product_image(product, 600, 600)

    context = {
        'product': product,
        'related': related,
        'tag_recs': tag_recs,
        'rating_form': rating_form,
        'user_rating': user_rating,
        'ratings': ratings,
        'rating_dist': rating_dist,
        'rating_dist_items': sorted(rating_dist.items(), reverse=True),
        'in_wishlist': in_wishlist,
        'product_img_url': product_img_url,
    }
    return render(request, 'shop/product_detail.html', context)


def search_view(request):
    query = request.GET.get('q', '').strip()
    brand_filter = request.GET.get('brand', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort = request.GET.get('sort', 'relevance')
    products = Product.objects.none()

    if query:
        words = [w for w in query.split() if len(w) > 1]

        name_exact = Product.objects.filter(is_active=True, is_approved=True, name__iexact=query)
        name_starts = Product.objects.filter(is_active=True, is_approved=True, name__istartswith=query)
        name_contains = Product.objects.filter(is_active=True, is_approved=True, name__icontains=query)
        brand_match = Product.objects.filter(is_active=True, is_approved=True, brand__name__icontains=query)
        desc_match = Product.objects.filter(is_active=True, is_approved=True).filter(
            Q(description__icontains=query) | Q(short_description__icontains=query) |
            Q(tags__icontains=query) | Q(category__name__icontains=query)
        )
        multi_word = Product.objects.none()
        if words and len(words) > 1:
            q = Q()
            for w in words:
                q |= Q(name__icontains=w) | Q(brand__name__icontains=w) | Q(tags__icontains=w)
            multi_word = Product.objects.filter(is_active=True, is_approved=True).filter(q)

        combined_ids_ordered = []
        seen = set()
        for qs in [name_exact, name_starts, name_contains, brand_match, multi_word, desc_match]:
            for pid in qs.values_list('id', flat=True):
                if pid not in seen:
                    combined_ids_ordered.append(pid)
                    seen.add(pid)

        products = Product.objects.filter(id__in=combined_ids_ordered).select_related('brand', 'category')

        if brand_filter:
            products = products.filter(brand__slug=brand_filter)
        if min_price:
            try:
                products = products.filter(price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                products = products.filter(price__lte=float(max_price))
            except ValueError:
                pass

        sort_map = {
            'price_asc': 'price',
            'price_desc': '-price',
            'popular': '-views_count',
            'newest': '-created_at',
        }
        if sort in sort_map:
            products = products.order_by(sort_map[sort])
        else:
            from django.db.models import Case, When, IntegerField
            preserved = Case(
                *[When(id=pid, then=pos) for pos, pid in enumerate(combined_ids_ordered)],
                output_field=IntegerField()
            )
            products = products.order_by(preserved)

    brands = Brand.objects.filter(is_active=True)
    paginator = Paginator(products, 12)
    page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'shop/search.html', {
        'query': query,
        'products': page,
        'result_count': paginator.count if query else 0,
        'brands': brands,
        'selected_brand': brand_filter,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
    })


def search_autocomplete(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query and len(query) >= 2:
        from .templatetags.shop_tags import product_image
        for p in Product.objects.filter(
            is_active=True, is_approved=True
        ).filter(
            Q(name__icontains=query) | Q(brand__name__icontains=query)
        ).select_related('brand', 'category')[:8]:
            results.append({
                'id': p.id,
                'name': p.name,
                'price': str(p.get_effective_price()),
                'slug': p.slug,
                'image': product_image(p, 80, 80),
                'category': p.category.name,
                'brand': p.brand.name if p.brand else '',
            })
    return JsonResponse({'results': results})


# ─── Auth ─────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('shop:home')
    role = request.GET.get('role', 'customer')

    if request.method == 'POST':
        role = request.POST.get('role', 'customer')
        FormClass = RetailerRegistrationForm if role == 'retailer' else CustomerRegistrationForm
        form = FormClass(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.email = form.cleaned_data.get('email', '')
            user.save()
            UserProfile.objects.create(
                user=user,
                role=role if role in ('customer', 'retailer') else 'customer',
                phone=form.cleaned_data.get('phone', ''),
            )
            if role == 'retailer':
                RetailerProfile.objects.create(
                    user=user,
                    business_name=form.cleaned_data.get('business_name', ''),
                    business_description=form.cleaned_data.get('business_description', ''),
                    business_address=form.cleaned_data.get('business_address', ''),
                    website=form.cleaned_data.get('website', ''),
                )
                login(request, user)
                messages.success(request, "Retailer account created! Your account is pending approval.")
                return redirect('shop:dashboard')
            login(request, user)
            messages.success(request, f"Welcome to TrendMart, {user.first_name or user.username}!")
            return redirect('shop:home')
        messages.error(request, "Please fix the errors below.")
    else:
        FormClass = RetailerRegistrationForm if role == 'retailer' else CustomerRegistrationForm
        form = FormClass()

    return render(request, 'shop/auth/register.html', {'form': form, 'role': role})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('shop:home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember_me')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if not remember:
                request.session.set_expiry(0)
            _merge_cart(request)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next', '')
            return redirect(next_url if next_url else 'shop:home')
        messages.error(request, "Invalid username or password.")
    return render(request, 'shop/auth/login.html')


def _merge_cart(request):
    session_key = request.session.session_key
    if not session_key:
        return
    try:
        anon_cart = Cart.objects.get(session_key=session_key, user=None)
        user_cart, _ = Cart.objects.get_or_create(user=request.user, defaults={'session_key': ''})
        for item in anon_cart.items.all():
            existing = user_cart.items.filter(product=item.product, size=item.size).first()
            if existing:
                existing.quantity += item.quantity
                existing.save()
            else:
                item.cart = user_cart
                item.save()
        anon_cart.delete()
    except Cart.DoesNotExist:
        pass


def logout_view(request):
    logout(request)
    messages.success(request, "You've been logged out. See you soon!")
    return redirect('shop:home')


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            request.user.first_name = form.cleaned_data.get('first_name', '')
            request.user.last_name = form.cleaned_data.get('last_name', '')
            request.user.email = form.cleaned_data.get('email', '')
            request.user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('shop:profile')
    else:
        form = UserProfileForm(instance=profile, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })
    return render(request, 'shop/auth/profile.html', {'form': form, 'profile': profile})


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.role == 'retailer':
        return retailer_dashboard(request)
    if profile.role == 'admin' or request.user.is_staff:
        return redirect('shop:admin_dashboard')
    return customer_dashboard(request)


@login_required
def customer_dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    recent_orders = Order.objects.filter(user=request.user)[:5]
    viewed_products = ViewedProduct.objects.filter(user=request.user).select_related('product')[:8]
    wishlist_items = WishlistItem.objects.filter(user=request.user).select_related('product')[:6]
    recent_ratings = ProductRating.objects.filter(user=request.user).select_related('product')[:4]
    recommendations = get_recommendations(request.user, limit=6)
    context = {
        'profile': profile,
        'recent_orders': recent_orders,
        'viewed_products': viewed_products,
        'wishlist_items': wishlist_items,
        'recent_ratings': recent_ratings,
        'recommendations': recommendations,
        'total_orders': Order.objects.filter(user=request.user).count(),
        'total_wishlist': WishlistItem.objects.filter(user=request.user).count(),
        'total_reviews': ProductRating.objects.filter(user=request.user).count(),
    }
    return render(request, 'shop/dashboard/customer.html', context)


@login_required
@retailer_required
def retailer_dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    my_products = Product.objects.filter(retailer=request.user).order_by('-created_at')
    pending_approval = not getattr(request.user, 'retailer_profile', None) or \
                       not request.user.retailer_profile.is_approved

    if request.method == 'POST' and 'add_product' in request.POST:
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.retailer = request.user
            product.is_approved = False
            product.save()
            messages.success(request, "Product submitted for approval!")
            return redirect('shop:retailer_dashboard')
        messages.error(request, "Please fix the errors.")
    else:
        form = ProductForm()

    context = {
        'profile': profile,
        'my_products': my_products,
        'product_form': form,
        'pending_approval': pending_approval,
        'total_products': my_products.count(),
        'active_products': my_products.filter(is_active=True, is_approved=True).count(),
        'pending_products': my_products.filter(is_approved=False).count(),
    }
    return render(request, 'shop/dashboard/retailer.html', context)


@login_required
@retailer_required
def retailer_edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk, retailer=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated!")
            return redirect('shop:retailer_dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'shop/dashboard/edit_product.html', {'form': form, 'product': product})


@login_required
@retailer_required
def retailer_delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk, retailer=request.user)
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted.")
    return redirect('shop:retailer_dashboard')


# ─── Cart ─────────────────────────────────────────────────────────────────────

def cart_view(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related('product').all()
    return render(request, 'shop/cart/cart.html', {'cart': cart, 'items': items})


@require_POST
def add_to_cart(request):
    product_id = request.POST.get('product_id')
    quantity = max(1, int(request.POST.get('quantity', 1)))
    size = request.POST.get('size', '')
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = get_or_create_cart(request)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, size=size, defaults={'quantity': quantity}
    )
    if not created:
        item.quantity += quantity
        item.save()
    # ── Push real-time stock update via WebSocket (if Channels is enabled) ──
    # After reducing stock, broadcast the new level to all visitors currently
    # viewing this product's detail page.  Silently skipped if Channels/Redis
    # is not installed so the cart still works without WebSocket infrastructure.
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'stock_{product.slug}',
                {'type': 'stock_update', 'stock': product.stock, 'slug': product.slug}
            )
    except Exception:
        pass  # Channels not installed or Redis unavailable — non-fatal

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'"{product.name}" added to cart!',
            'cart_count': cart.get_item_count(),
        })
    messages.success(request, f'"{product.name}" added to cart!')
    return redirect('shop:cart')


@require_POST
def remove_from_cart(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    name = item.product.name
    item.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'cart_count': cart.get_item_count(), 'cart_total': str(cart.get_total())})
    messages.success(request, f'"{name}" removed from cart.')
    return redirect('shop:cart')


@require_POST
def update_cart(request, item_id):
    import json as _json
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    try:
        body = _json.loads(request.body)
        qty = int(body.get('quantity', 1))
    except Exception:
        qty = int(request.POST.get('quantity', 1))
    if qty <= 0:
        item.delete()
        subtotal = '0'
    else:
        item.quantity = qty
        item.save()
        subtotal = str(item.get_subtotal())
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'subtotal': subtotal,
            'cart_count': cart.get_item_count(),
            'cart_total': str(cart.get_total()),
        })
    return redirect('shop:cart')


# ─── Checkout & Orders ────────────────────────────────────────────────────────

def checkout(request):
    cart = get_or_create_cart(request)
    if cart.get_item_count() == 0:
        messages.warning(request, "Your cart is empty.")
        return redirect('shop:cart')

    initial = {}
    if request.user.is_authenticated:
        u = request.user
        initial = {'full_name': u.get_full_name(), 'email': u.email}
        try:
            p = u.profile
            initial.update({'phone': p.phone, 'address': p.address, 'city': p.city,
                            'country': p.country, 'postal_code': p.postal_code})
        except UserProfile.DoesNotExist:
            pass

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=form.cleaned_data['full_name'],
                email=form.cleaned_data['email'],
                phone=form.cleaned_data.get('phone', ''),
                address=form.cleaned_data['address'],
                city=form.cleaned_data['city'],
                country=form.cleaned_data['country'],
                postal_code=form.cleaned_data['postal_code'],
                notes=form.cleaned_data.get('notes', ''),
                total_amount=cart.get_total(),
            )
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    product_price=item.product.get_effective_price(),
                    quantity=item.quantity,
                    size=item.size,
                )
                if item.product.stock >= item.quantity:
                    item.product.stock -= item.quantity
                    item.product.save(update_fields=['stock'])
            cart.items.all().delete()
            # Send order confirmation email (fires async-style; failures are swallowed)
            try:
                from .emails import send_order_confirmation
                send_order_confirmation(order)
            except Exception:
                pass  # Never let email failure block checkout
            return redirect('shop:order_success', order_number=order.order_number)
        messages.error(request, "Please fix the form errors.")
    else:
        form = CheckoutForm(initial=initial)

    items = cart.items.select_related('product').all()
    return render(request, 'shop/orders/checkout.html', {'form': form, 'cart': cart, 'items': items})


def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'shop/orders/order_success.html', {'order': order})


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'shop/orders/order_list.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'shop/orders/order_detail.html', {'order': order})


# ─── Wishlist ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def toggle_wishlist(request):
    product_id = request.POST.get('product_id')
    product = get_object_or_404(Product, id=product_id)
    item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.delete()
        action = 'removed'
    else:
        action = 'added'
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        total = WishlistItem.objects.filter(user=request.user).count()
        return JsonResponse({'success': True, 'action': action, 'total': total})
    messages.success(request, f'Product {action} {"to" if action == "added" else "from"} wishlist.')
    return redirect('shop:product_detail', slug=product.slug)


@login_required
def wishlist_view(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('product')
    return render(request, 'shop/wishlist.html', {'items': items})


# ─── Ratings ──────────────────────────────────────────────────────────────────

@login_required
@require_POST
def rate_product(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    rating_val = int(request.POST.get('rating', 0))
    review_text = request.POST.get('review', '').strip()

    if not 1 <= rating_val <= 5:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid rating value.'})
        messages.error(request, "Invalid rating.")
        return redirect('shop:product_detail', slug=slug)

    has_purchased = Order.objects.filter(
        user=request.user, items__product=product
    ).exists()

    rating, created = ProductRating.objects.update_or_create(
        product=product, user=request.user,
        defaults={'rating': rating_val, 'review': review_text, 'is_verified_purchase': has_purchased}
    )

    photo = request.FILES.get('review_photo')
    if photo:
        rating.review_photo = photo
        rating.save(update_fields=['review_photo'])

    avg = product.get_avg_rating()
    count = product.get_rating_count()

    photo_url = rating.review_photo.url if rating.review_photo else ''

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'avg_rating': avg,
            'count': count,
            'created': created,
            'username': request.user.get_full_name() or request.user.username,
            'review': review_text,
            'rating': rating_val,
            'photo_url': photo_url,
        })
    messages.success(request, "Your review has been submitted!")
    return redirect('shop:product_detail', slug=slug)


@login_required
@require_POST
def mark_review_helpful(request, review_id):
    from .models import ProductRating
    review = get_object_or_404(ProductRating, id=review_id)
    if review.user == request.user:
        return JsonResponse({'success': False, 'error': "You can't mark your own review as helpful."})
    review.helpful_count += 1
    review.save(update_fields=['helpful_count'])
    return JsonResponse({'success': True, 'helpful_count': review.helpful_count})


# ─── AI Assistant ─────────────────────────────────────────────────────────────
# Conversation history is stored per-user in the Django session so the AI
# remembers what was said earlier in the same chat session (like ChatGPT).
# Max 10 message pairs kept to avoid token limits.

AI_MAX_HISTORY = 10  # maximum user+assistant turns to keep in session memory

def ai_assistant(request):
    """
    POST endpoint for the TrendMart AI assistant chat widget.
    Tries the OpenRouter API first (real LLM); falls back to the rule-based
    keyword engine if the API call fails or no key is configured.
    Supports 'clear_history' action to reset conversation memory.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_msg = data.get('message', '').strip()
            action = data.get('action', '')
        except (json.JSONDecodeError, AttributeError):
            user_msg = ''
            action = ''

        # Allow the frontend to wipe conversation memory (e.g. "New chat" button)
        if action == 'clear_history':
            request.session.pop('ai_history', None)
            return JsonResponse({'reply': "Chat cleared! How can I help you? 😊"})

        from django.conf import settings
        api_key = getattr(settings, 'OPENROUTER_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '')

        if api_key and user_msg:
            response = _ai_response_openrouter(request, user_msg, api_key)
        else:
            response = _ai_response(request, user_msg.lower())

        return JsonResponse({'reply': response})
    return JsonResponse({'error': 'Invalid request'}, status=400)


def _ai_response_openrouter(request, user_msg, api_key):
    """
    Sends the conversation to OpenRouter's OpenAI-compatible API.
    Maintains a rolling window of conversation history in the session so the
    AI has context from earlier in the same chat (memory across turns).
    On any network/API failure, falls back to the keyword-based engine.
    """
    import urllib.request as urlreq
    import json as json_lib
    from django.conf import settings

    # ── Build live context for the system prompt ──────────────
    cart = get_or_create_cart(request)
    cart_summary = (
        f"{cart.get_item_count()} item(s), total ${cart.get_total():.2f}"
        if cart.get_item_count() else "empty"
    )
    user_name = request.user.first_name if request.user.is_authenticated else "guest"
    is_logged_in = request.user.is_authenticated

    # Fetch popular products to give the AI real catalogue awareness
    recent_products = list(
        Product.objects.filter(is_active=True, is_approved=True)
        .order_by('-views_count')[:8]
        .values('name', 'price', 'sale_price', 'slug', 'category__name')
    )
    products_ctx = '; '.join([
        f"{p['name']} (${p['sale_price'] or p['price']}, {p['category__name']}) → /products/{p['slug']}/"
        for p in recent_products
    ])

    # Fetch sale items for deal-awareness
    sale_products = list(
        Product.objects.filter(is_active=True, is_approved=True, sale_price__isnull=False)
        .order_by('?')[:4]
        .values('name', 'price', 'sale_price', 'slug')
    )
    sales_ctx = '; '.join([
        f"{p['name']} was ${p['price']} now ${p['sale_price']}"
        for p in sale_products
    ]) or "None currently"

    # Order history summary for logged-in users
    orders_ctx = "Not logged in"
    if is_logged_in:
        recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:3]
        if recent_orders.exists():
            orders_ctx = '; '.join([
                f"#{o.order_number} ({o.get_status_display()}, ${o.total_amount})"
                for o in recent_orders
            ])
        else:
            orders_ctx = "No orders yet"

    system_prompt = f"""You are TrendMart AI — an intelligent, friendly, and knowledgeable shopping assistant \
for TrendMart, a modern e-commerce platform owned by George Papasotiriou.

USER CONTEXT:
- Name: {user_name} | Logged in: {is_logged_in}
- Cart: {cart_summary}
- Recent orders: {orders_ctx}

LIVE CATALOGUE (popular products):
{products_ctx}

CURRENT SALES:
{sales_ctx}

YOUR CAPABILITIES:
- Find, recommend, and compare products from the TrendMart catalogue
- Help with orders, returns, wishlist, account management
- Answer questions about shipping (standard 3-5 days, express 1-2 days, free over $50), returns (30 days), warranty
- Give personalised recommendations based on conversation context
- Explain product features and help users decide between options

FORMATTING RULES:
- When referencing a product, use: 🔗[Product Name — $price](/products/product-slug/)
- Use **bold** for key terms, bullet lists for multiple items
- Keep responses concise (under 250 words) but thorough
- Always end with a helpful follow-up question or suggestion
- Never invent products not in the catalogue — say you'll search instead

PERSONALITY: Warm, enthusiastic, expert. Like a knowledgeable friend who loves shopping. \
Use emojis sparingly but effectively. Be honest about limitations."""

    # ── Retrieve/update conversation history from session ─────
    history = request.session.get('ai_history', [])

    # Append the new user message to the rolling history
    history.append({'role': 'user', 'content': user_msg})

    # Trim to last AI_MAX_HISTORY * 2 messages (user+assistant pairs)
    if len(history) > AI_MAX_HISTORY * 2:
        history = history[-(AI_MAX_HISTORY * 2):]

    # Construct the full messages list: system + history
    messages = [{'role': 'system', 'content': system_prompt}] + history

    payload = {
        'model': getattr(settings, 'OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
        'messages': messages,
        'max_tokens': 400,
        'temperature': 0.7,
        # OpenRouter headers for analytics/attribution (optional)
    }

    try:
        req = urlreq.Request(
            # OpenRouter uses the same endpoint format as OpenAI
            'https://openrouter.ai/api/v1/chat/completions',
            data=json_lib.dumps(payload).encode(),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                # Optional OpenRouter headers for usage tracking
                'HTTP-Referer': 'https://trendmart.com',
                'X-Title': 'TrendMart AI Assistant',
            },
            method='POST'
        )
        with urlreq.urlopen(req, timeout=12) as resp:
            result = json_lib.loads(resp.read().decode())
            ai_reply = result['choices'][0]['message']['content']

        # Save the assistant's reply into history and persist in session
        history.append({'role': 'assistant', 'content': ai_reply})
        request.session['ai_history'] = history
        request.session.modified = True

        return ai_reply

    except Exception:
        # If the API call fails for any reason, use the keyword fallback
        # and still save a fallback message to history
        fallback = _ai_response(request, user_msg.lower())
        history.append({'role': 'assistant', 'content': fallback})
        request.session['ai_history'] = history
        request.session.modified = True
        return fallback


def _ai_response(request, msg):
    import re

    def products_to_links(qs):
        return '\n'.join([
            f"🔗[{p.name} — ${p.get_effective_price()}](/products/{p.slug}/)"
            for p in qs
        ])

    # ── Greetings ────────────────────────────────────────────
    if any(g in msg for g in ('hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'howdy', 'sup')):
        name = request.user.first_name if request.user.is_authenticated else 'there'
        return (f"Hi {name}! 👋 Welcome to **TrendMart**!\n\n"
                f"I can help you:\n"
                f"• 🔍 Find & compare products\n"
                f"• 🏷️ Discover current deals\n"
                f"• 📦 Track your orders\n"
                f"• 💡 Get personalised recommendations\n\n"
                f"What are you shopping for today?")

    # ── Personalised recommendations ─────────────────────────
    if any(w in msg for w in ('recommend', 'suggestion', 'suggest', 'what should', 'what do you suggest', 'best for me', 'personaliz', 'for me')):
        if request.user.is_authenticated:
            recs = get_recommendations(request.user, limit=4)
            if recs:
                links = products_to_links(list(recs)[:4])
                return f"Based on your browsing history, here are picks I think you'll love:\n\n{links}\n\nWant me to narrow these down by category or budget?"
        top = Product.objects.filter(is_active=True, is_approved=True).order_by('-views_count')[:4]
        links = products_to_links(top)
        return f"Here are our **most popular products** right now:\n\n{links}\n\nLog in for personalised recommendations based on your taste! 😊"

    # ── Order tracking ───────────────────────────────────────
    if any(w in msg for w in ('order', 'my order', 'track', 'shipping', 'delivery', 'dispatched', 'sent', 'arrive', 'when will')):
        if request.user.is_authenticated:
            orders = Order.objects.filter(user=request.user).order_by('-created_at')[:3]
            if orders.exists():
                lines = '\n'.join([f"• Order **#{o.order_number}** → **{o.get_status_display()}** (${o.total_amount:.2f})" for o in orders])
                return f"Here are your recent orders:\n\n{lines}\n\nView all orders and full details in your **[Dashboard](/dashboard/)**."
            return "You don't have any orders yet! Browse our products and start shopping 🛍️"
        return "Please **[log in](/login/)** to track your orders. Your order history and live status updates will be there waiting for you!"

    # ── Cart summary ─────────────────────────────────────────
    if any(w in msg for w in ('cart', 'basket', 'bag', 'checkout', 'how much', 'total')):
        cart = get_or_create_cart(request)
        count = cart.get_item_count()
        total = cart.get_total()
        if count == 0:
            return "Your cart is empty! 🛒 Browse our products and add something you love.\n\n🔗[Browse All Products](/products/)"
        return f"You have **{count} item(s)** in your cart totalling **${total:.2f}**.\n\n🔗[View Cart & Checkout](/cart/)\n\nNeed help finding anything else?"

    # ── Price / budget queries ───────────────────────────────
    budget_match = re.search(r'under\s*\$?(\d+)', msg) or re.search(r'less than\s*\$?(\d+)', msg) or re.search(r'below\s*\$?(\d+)', msg)
    if budget_match or any(w in msg for w in ('budget', 'affordable', 'cheap', 'cheapest', 'low price')):
        budget = float(budget_match.group(1)) if budget_match else 100
        products = Product.objects.filter(
            is_active=True, is_approved=True, price__lte=budget
        ).order_by('price')[:5]
        if products.exists():
            links = products_to_links(products)
            return f"Great picks under **${budget:.0f}**:\n\n{links}"
        return f"No products found under ${budget:.0f} right now. Try a higher budget or check our **[deals page](/products/?sort=price_asc)**."

    # ── Deals and discounts ──────────────────────────────────
    if any(w in msg for w in ('sale', 'discount', 'offer', 'deal', 'hot deal', 'promo', 'coupon', 'bargain', 'best price')):
        sales = Product.objects.filter(is_active=True, is_approved=True, sale_price__isnull=False).order_by('?')[:5]
        if sales:
            links = '\n'.join([f"🔗[{p.name} — ${p.sale_price} ~~${p.price}~~ ({p.get_discount_percentage()}% off)](/products/{p.slug}/)" for p in sales])
            return f"🔥 **Today's hottest deals:**\n\n{links}\n\nMore deals available in the **[Products page](/products/)**!"
        return "Check our **[Products page](/products/)** for the latest deals and discounts!"

    # ── Brand search ─────────────────────────────────────────
    from .models import Brand
    brand_names = list(Brand.objects.filter(is_active=True).values_list('name', flat=True))
    matched_brand = next((b for b in brand_names if b.lower() in msg), None)
    if matched_brand or any(w in msg for w in ('brand', 'apple products', 'samsung products', 'nike products')):
        if matched_brand:
            products = Product.objects.filter(
                is_active=True, is_approved=True, brand__name__iexact=matched_brand
            )[:5]
            if products.exists():
                links = products_to_links(products)
                return f"Here are **{matched_brand}** products available on TrendMart:\n\n{links}"
        return "We carry many top brands including Apple, Samsung, Nike, Adidas, Sony, and more! Which brand are you interested in?"

    # ── Category browse ──────────────────────────────────────
    cat_keywords = {
        'electronics': 'Electronics', 'phone': 'Smartphones', 'smartphone': 'Smartphones',
        'laptop': 'Laptops', 'computer': 'Laptops', 'headphone': 'Headphones', 'earphone': 'Headphones',
        'tablet': 'Tablets', 'fashion': 'Fashion', 'clothing': "Men's Clothing",
        'shoe': 'Shoes', 'sneaker': 'Shoes', 'watch': 'Accessories',
        'home': 'Home & Garden', 'furniture': 'Furniture', 'kitchen': 'Kitchen',
        'sport': 'Sports & Outdoors', 'fitness': 'Fitness', 'gym': 'Fitness',
        'beauty': 'Beauty & Health', 'skincare': 'Skincare', 'makeup': 'Makeup',
        'game': 'Board Games', 'lego': 'Action Figures', 'toy': 'Toys & Games',
        'camera': 'Cameras', 'photo': 'Cameras', 'smart home': 'Smart Home',
        'pet': 'Pet Supplies', 'book': 'Books', 'car': 'Car Accessories',
    }
    for kw, cat_name in cat_keywords.items():
        if kw in msg:
            products = Product.objects.filter(
                is_active=True, is_approved=True,
                category__name__iexact=cat_name
            )[:5]
            if not products.exists():
                products = Product.objects.filter(
                    is_active=True, is_approved=True,
                    category__name__icontains=kw
                )[:5]
            if products.exists():
                links = products_to_links(products)
                return f"Here are popular **{cat_name}** products:\n\n{links}\n\nBrowse the full **[{cat_name}](/products/)** collection!"
            break

    # ── Wishlist ─────────────────────────────────────────────
    if any(w in msg for w in ('wishlist', 'wish list', 'saved', 'favorite', 'favourite')):
        if request.user.is_authenticated:
            from .models import WishlistItem
            count = WishlistItem.objects.filter(user=request.user).count()
            if count:
                return f"You have **{count} item(s)** saved in your wishlist! 💜\n\n🔗[View Wishlist](/wishlist/)"
            return "Your wishlist is empty. Click the ❤️ heart on any product to save it for later!"
        return "Log in to create your personal wishlist and save products for later!\n\n🔗[Log in](/login/)"

    # ── Compare products ─────────────────────────────────────
    if any(w in msg for w in ('compare', 'difference', 'better', 'vs', 'versus', 'which is better', 'which should i')):
        return ("I can help you compare products! 🔍\n\n"
                "Tell me the two products you'd like to compare — for example:\n"
                "**iPhone 15 Pro vs Samsung Galaxy S24 Ultra**\n\n"
                "Or describe what matters to you (camera, battery, price) and I'll suggest the best match!")

    # ── Shipping / delivery info ─────────────────────────────
    if any(w in msg for w in ('how long', 'when', 'estimated', 'arrive', 'dispatch')):
        return ("📦 **Shipping Information:**\n\n"
                "• Standard delivery: **3–5 business days**\n"
                "• Express delivery: **1–2 business days**\n"
                "• Free shipping on orders over **$50**\n\n"
                "Track your existing orders in your **[Dashboard](/dashboard/)**.")

    # ── Return / refund ──────────────────────────────────────
    if any(w in msg for w in ('return', 'refund', 'exchange', 'warranty', 'broken', 'damaged', 'faulty', 'wrong item')):
        return ("↩️ **TrendMart Return Policy:**\n\n"
                "• **30-day** hassle-free returns on all items\n"
                "• Items must be unused and in original packaging\n"
                "• Warranty claims handled within **5 business days**\n"
                "• Damaged/faulty items replaced free of charge\n\n"
                "Contact our support team at **support@trendmart.com** for assistance.")

    # ── Account / profile ────────────────────────────────────
    if any(w in msg for w in ('account', 'profile', 'register', 'sign up', 'signup', 'login', 'log in', 'password', 'forgot')):
        if request.user.is_authenticated:
            return (f"You're logged in as **{request.user.first_name or request.user.username}** 👤\n\n"
                    f"• 🔗[Edit Profile](/profile/)\n"
                    f"• 🔗[My Dashboard](/dashboard/)\n"
                    f"• 🔗[Order History](/orders/)")
        return ("Create a free TrendMart account to unlock:\n\n"
                "✅ Personalised recommendations\n"
                "✅ Order tracking & history\n"
                "✅ Wishlist & saved searches\n"
                "✅ Exclusive member deals\n\n"
                "🔗[Register Now](/register/) or 🔗[Log In](/login/)")

    # ── Help & support ───────────────────────────────────────
    if any(w in msg for w in ('help', 'support', 'contact', 'problem', 'issue', 'stuck', "can't", "cannot", 'error')):
        return ("I'm here to help! 🤝 Here's what I can assist with:\n\n"
                "• **Product search** — describe what you want\n"
                "• **Order issues** — tracking, returns, refunds\n"
                "• **Account help** — login, profile, password\n"
                "• **Deals & recommendations** — just ask!\n\n"
                "For complex issues: **support@trendmart.com**\n"
                "Response time: within **24 hours**")

    # ── Thank you / farewell ─────────────────────────────────
    if any(w in msg for w in ('thank', 'thanks', 'ty', 'cheers', 'bye', 'goodbye', 'see you', 'cya')):
        name = request.user.first_name if request.user.is_authenticated else ''
        return f"You're welcome{', ' + name if name else ''}! 🛍️ Happy shopping at **TrendMart**! Come back anytime — I'm always here to help."

    # ── Compliments / misc ───────────────────────────────────
    if any(w in msg for w in ('amazing', 'great', 'awesome', 'love', 'perfect', 'excellent', 'fantastic')):
        return "Thank you so much! 😊 That really means a lot. Now, is there anything I can help you find today?"

    # ── Product name search (flexible) ──────────────────────
    words = [w for w in msg.split() if len(w) > 2]
    products = Product.objects.filter(is_active=True, is_approved=True).filter(
        Q(name__icontains=msg) | Q(brand__name__icontains=msg) | Q(short_description__icontains=msg)
    )[:4]
    if not products.exists() and words:
        q = Q()
        for w in words[:3]:
            q |= Q(name__icontains=w) | Q(brand__name__icontains=w)
        products = Product.objects.filter(is_active=True, is_approved=True).filter(q)[:4]

    if products.exists():
        links = products_to_links(products)
        return f"I found these products for you:\n\n{links}\n\nNeed more options? Try **[searching here](/search/?q={msg.replace(' ', '+')})** or tell me more about what you're looking for!"

    # ── Category name fallback ───────────────────────────────
    cats = Category.objects.filter(is_active=True, name__icontains=msg)[:2]
    if cats.exists():
        cat_links = '\n'.join([f"🔗[Browse {c.name}](/products/)" for c in cats])
        return f"Found the **{cats.first().name}** category!\n\n{cat_links}"

    # ── Fallback ─────────────────────────────────────────────
    return ("I didn't quite catch that, but I'm here to help! 🤔\n\n"
            "Try asking me:\n"
            "• **\"Show me laptops under $1000\"**\n"
            "• **\"What's on sale today?\"**\n"
            "• **\"Recommend me something for gaming\"**\n"
            "• **\"Track my order\"**\n"
            "• **\"Compare iPhone vs Samsung\"**\n\n"
            "Or just type a product name and I'll find it for you!")


# ─── Admin Panel ──────────────────────────────────────────────────────────────

@admin_required
def admin_dashboard(request):
    """
    Admin overview dashboard with stats, recent orders, pending approvals,
    and Chart.js analytics data (revenue trends + top products by revenue).
    All heavy queries are done here so the template stays logic-free.
    """
    from django.db.models.functions import TruncDate
    import json as _json
    from datetime import timedelta

    # ── Revenue chart: last 30 days, one data point per day ──
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_revenue = (
        Order.objects
        .filter(created_at__gte=thirty_days_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(revenue=Sum('total_amount'), count=Count('id'))
        .order_by('day')
    )
    # Build a complete 30-day date series (fill missing days with 0)
    date_map = {entry['day']: {'revenue': float(entry['revenue'] or 0), 'count': entry['count']}
                for entry in daily_revenue}
    chart_labels = []
    chart_revenue = []
    chart_orders = []
    for i in range(30):
        day = (timezone.now() - timedelta(days=29 - i)).date()
        chart_labels.append(day.strftime('%b %d'))
        data = date_map.get(day, {'revenue': 0, 'count': 0})
        chart_revenue.append(data['revenue'])
        chart_orders.append(data['count'])

    # ── Top 8 products by total revenue generated from OrderItems ──
    top_products = (
        OrderItem.objects
        .values('product_name')
        .annotate(total_revenue=Sum(F('product_price') * F('quantity')),
                  total_sold=Sum('quantity'))
        .order_by('-total_revenue')[:8]
    )

    # ── Revenue by category ──
    category_revenue = (
        OrderItem.objects
        .filter(product__isnull=False)
        .values('product__category__name')
        .annotate(revenue=Sum(F('product_price') * F('quantity')))
        .order_by('-revenue')[:6]
    )

    # ── Summary stats ──
    total_revenue = Order.objects.aggregate(t=Sum('total_amount'))['t'] or 0

    context = {
        'total_products': Product.objects.count(),
        'total_orders': Order.objects.count(),
        'total_users': User.objects.count(),
        'total_retailers': RetailerProfile.objects.count(),
        'total_revenue': total_revenue,
        'recent_orders': Order.objects.select_related('user').order_by('-created_at')[:10],
        'pending_retailers': RetailerProfile.objects.filter(is_approved=False).select_related('user'),
        'pending_products': Product.objects.filter(is_approved=False).select_related('retailer')[:10],
        # Chart.js data — JSON-encoded for safe embedding in <script> tags
        'chart_labels_json': _json.dumps(chart_labels),
        'chart_revenue_json': _json.dumps(chart_revenue),
        'chart_orders_json': _json.dumps(chart_orders),
        'top_products_json': _json.dumps([
            {'name': p['product_name'], 'revenue': float(p['total_revenue'] or 0), 'sold': p['total_sold'] or 0}
            for p in top_products
        ]),
        'category_revenue_json': _json.dumps([
            {'name': p['product__category__name'] or 'Uncategorised', 'revenue': float(p['revenue'] or 0)}
            for p in category_revenue
        ]),
    }
    return render(request, 'shop/admin_panel/dashboard.html', context)


@admin_required
def admin_products(request):
    products = Product.objects.select_related('category', 'brand', 'retailer').all()
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    if status_filter == 'pending':
        products = products.filter(is_approved=False)
    elif status_filter == 'active':
        products = products.filter(is_approved=True, is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)
    paginator = Paginator(products, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'shop/admin_panel/products.html', {
        'products': page, 'query': query, 'status_filter': status_filter
    })


@admin_required
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated.")
            return redirect('shop:admin_products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'shop/admin_panel/product_form.html', {'form': form, 'product': product})


@admin_required
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted.")
    return redirect('shop:admin_products')


@admin_required
def admin_product_approve(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_approved = True
    product.save(update_fields=['is_approved'])
    messages.success(request, f'Product "{product.name}" approved.')
    return redirect('shop:admin_dashboard')


@admin_required
def admin_categories(request):
    edit_category = None
    edit_pk = request.GET.get('edit')
    if edit_pk:
        edit_category = get_object_or_404(Category, pk=edit_pk)

    if request.method == 'POST':
        pk = request.POST.get('category_id')
        if pk:
            cat = get_object_or_404(Category, pk=pk)
            form = CategoryForm(request.POST, request.FILES, instance=cat)
        else:
            form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Category saved.")
            return redirect('shop:admin_categories')
    elif edit_category:
        form = CategoryForm(instance=edit_category)
    else:
        form = CategoryForm()
    categories = Category.objects.all()
    return render(request, 'shop/admin_panel/categories.html', {
        'categories': categories, 'form': form, 'edit_category': edit_category
    })


@admin_required
def admin_category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, "Category deleted.")
    return redirect('shop:admin_categories')


@admin_required
def admin_users(request):
    users = User.objects.select_related('profile').order_by('-date_joined')
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query))
    if role_filter == 'retailer':
        users = users.filter(profile__role='retailer')
    elif role_filter == 'admin':
        users = users.filter(Q(profile__role='admin') | Q(is_staff=True))
    elif role_filter == 'customer':
        users = users.filter(profile__role='customer')
    paginator = Paginator(users, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    pending_retailers = RetailerProfile.objects.filter(is_approved=False).select_related('user')
    return render(request, 'shop/admin_panel/users.html', {
        'users': page, 'query': query, 'role_filter': role_filter,
        'pending_retailers': pending_retailers,
    })


@admin_required
def admin_approve_retailer(request, user_id):
    retailer_profile = get_object_or_404(RetailerProfile, user_id=user_id)
    retailer_profile.is_approved = True
    retailer_profile.save(update_fields=['is_approved'])
    messages.success(request, f'Retailer "{retailer_profile.business_name}" approved.')
    return redirect('shop:admin_dashboard')


@admin_required
def admin_orders(request):
    orders = Order.objects.select_related('user').prefetch_related('items').all()
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    if query:
        orders = orders.filter(Q(order_number__icontains=query) | Q(full_name__icontains=query) | Q(email__icontains=query))
    if status_filter:
        orders = orders.filter(status=status_filter)
    paginator = Paginator(orders, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'shop/admin_panel/orders.html', {
        'orders': page, 'query': query, 'status_filter': status_filter
    })


@admin_required
def admin_order_status(request, order_number):
    """
    Update an order's status from the admin panel.
    When status changes to 'shipped', automatically sends a dispatch
    notification email to the customer.
    """
    order = get_object_or_404(Order, order_number=order_number)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(Order.STATUS_CHOICES):
            old_status = order.status
            order.status = status
            order.save(update_fields=['status'])
            messages.success(request, f"Order #{order_number} status updated to {status}.")
            # Trigger dispatch email when order first moves to 'shipped'
            if status == 'shipped' and old_status != 'shipped' and order.email:
                try:
                    from .emails import send_dispatch_notification
                    send_dispatch_notification(order)
                    messages.info(request, f"Dispatch email sent to {order.email}.")
                except Exception:
                    pass  # Email failures are non-fatal
    return redirect('shop:admin_orders')
