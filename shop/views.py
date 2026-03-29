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
    RetailerProfile, ProductVariant, AIConversation,
    LoyaltyPoints, LoyaltyTransaction, Notification, PromoCode,
    SearchSynonym, SearchLog, ProductQuestion, ProductAnswer,
    UserAddress, WishlistShareToken, StockNotification,
    NewsletterSubscriber, AuditLog, ReviewReply, Collection,
    Referral, ABTest, ProductTrendScore,
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
# Conversation history is stored in two ways:
#   1. DB (AIConversation model) — for authenticated users; persists across devices
#   2. Django session — for anonymous users; lost when session expires
# Max AI_MAX_HISTORY message pairs are sent to OpenRouter to stay within token limits.
# The AI also reads/writes ai_preferences on UserProfile for long-term memory.

AI_MAX_HISTORY = 12  # number of user+assistant turn pairs to keep in context window


# ── Helper: load conversation history ────────────────────────────────────────
def _get_conversation_history(request):
    """
    Return recent conversation history as a list of {'role', 'content'} dicts.
    Authenticated users: loaded from AIConversation DB rows (cross-device).
    Anonymous users: loaded from the Django session (in-memory, temporary).
    """
    if request.user.is_authenticated:
        rows = AIConversation.objects.filter(
            user=request.user
        ).order_by('-created_at')[:AI_MAX_HISTORY * 2]
        return [{'role': r.role, 'content': r.content} for r in reversed(rows)]
    return request.session.get('ai_history', [])


# ── Helper: save a message pair to the appropriate history store ──────────────
def _save_conversation(request, user_msg, assistant_reply):
    """
    Persist user message + assistant reply in DB (logged-in) or session (anon).
    """
    if request.user.is_authenticated:
        AIConversation.objects.create(user=request.user, role='user', content=user_msg)
        AIConversation.objects.create(user=request.user, role='assistant', content=assistant_reply)
        # Trim to last AI_MAX_HISTORY * 2 rows to avoid unbounded growth
        all_ids = list(
            AIConversation.objects.filter(user=request.user)
            .order_by('created_at').values_list('id', flat=True)
        )
        if len(all_ids) > AI_MAX_HISTORY * 2:
            AIConversation.objects.filter(id__in=all_ids[:len(all_ids) - AI_MAX_HISTORY * 2]).delete()
    else:
        history = request.session.get('ai_history', [])
        history.append({'role': 'user', 'content': user_msg})
        history.append({'role': 'assistant', 'content': assistant_reply})
        if len(history) > AI_MAX_HISTORY * 2:
            history = history[-(AI_MAX_HISTORY * 2):]
        request.session['ai_history'] = history
        request.session.modified = True


# ── Helper: detect frustrated sentiment in the last few messages ──────────────
# Returns True if the user appears frustrated so the system prompt can include
# an empathy instruction and offer escalation to human support.
_FRUSTRATION_WORDS = {
    'terrible', 'broken', 'wrong', 'fraud', 'scam', 'disappointed',
    'useless', 'awful', 'horrible', 'furious', 'angry', 'refund', 'cancel',
    'never again', 'worst', 'hate', 'ridiculous', 'unacceptable', 'disgusting',
}

def _is_frustrated(history):
    """Return True if any of the last 4 user messages contain frustration words."""
    user_msgs = [m['content'].lower() for m in history if m['role'] == 'user'][-4:]
    for msg in user_msgs:
        if any(w in msg for w in _FRUSTRATION_WORDS):
            return True
    return False


# ── Helper: extract preferences from conversation and persist them ─────────────
def _extract_and_save_preferences(request, history):
    """
    Scans recent conversation for stated preferences (brands, budget, sizes) and
    updates the UserProfile.ai_preferences JSON field.  Only runs for logged-in users.
    Called after each assistant reply so preferences accumulate over time.
    """
    if not request.user.is_authenticated:
        return
    import re
    user_texts = ' '.join(m['content'].lower() for m in history if m['role'] == 'user')
    prefs = {}
    # Detect budget mentions: "under $200", "budget of $150", "max $300"
    budget_match = re.search(r'(?:under|below|max|budget[^\d]*|less than)\s*\$?(\d+)', user_texts)
    if budget_match:
        prefs['budget_max'] = int(budget_match.group(1))
    # Detect size mentions: "size 10", "size M", "EU 42"
    size_match = re.search(r'(?:size|eu)\s*([a-z0-9]+)', user_texts)
    if size_match:
        prefs.setdefault('sizes', {})['general'] = size_match.group(1).upper()
    try:
        profile = request.user.profile
        if prefs:
            existing = profile.ai_preferences or {}
            existing.update(prefs)
            profile.ai_preferences = existing
            profile.save(update_fields=['ai_preferences'])
    except UserProfile.DoesNotExist:
        pass


def ai_assistant(request):
    """
    POST endpoint for the TrendMart AI chat widget.
    Supports the following actions (sent as JSON body field 'action'):
      - (none)          : regular chat message — calls OpenRouter or keyword fallback
      - 'clear_history' : deletes DB history (auth) or session history (anon)
      - 'export'        : returns the full conversation as plain text for download
    Additional body fields:
      - 'message'    : the user's chat text (string)
      - 'image_data' : base64-encoded image for vision search (string, optional)
      - 'is_frustrated': frontend sentiment flag (bool) — added when negativity detected
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, AttributeError):
        data = {}

    user_msg = data.get('message', '').strip()
    action = data.get('action', '')
    image_data = data.get('image_data', '')      # base64 image for vision requests
    frontend_frustrated = data.get('is_frustrated', False)  # JS sentiment flag

    # ── Action: clear history ─────────────────────────────────
    if action == 'clear_history':
        request.session.pop('ai_history', None)
        if request.user.is_authenticated:
            AIConversation.objects.filter(user=request.user).delete()
        return JsonResponse({'reply': "Chat cleared! ✨ Fresh start — what can I help you find today?"})

    # ── Action: export history as plain text ──────────────────
    if action == 'export':
        history = _get_conversation_history(request)
        lines = []
        for msg in history:
            label = 'You' if msg['role'] == 'user' else 'TrendMart AI'
            lines.append(f"[{label}]: {msg['content']}")
        export_text = '\n\n'.join(lines) if lines else 'No conversation history to export.'
        return JsonResponse({'text': export_text})

    from django.conf import settings
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '')

    if api_key and (user_msg or image_data):
        # Pass the frontend frustration flag so the system prompt can adapt
        response, products_meta = _ai_response_openrouter(
            request, user_msg, api_key,
            image_data=image_data,
            frontend_frustrated=frontend_frustrated,
        )
    else:
        response = _ai_response(request, user_msg.lower())
        products_meta = []

    # Persist conversation to DB / session
    if user_msg or image_data:
        _save_conversation(request, user_msg or '[image uploaded]', response)

    # After saving, scan for preference signals in the history
    history = _get_conversation_history(request)
    _extract_and_save_preferences(request, history)

    return JsonResponse({'reply': response, 'products': products_meta})


def _ai_response_openrouter(request, user_msg, api_key, image_data='', frontend_frustrated=False):
    """
    Sends the conversation to OpenRouter's OpenAI-compatible API and returns
    (reply_text, products_metadata_list).

    Enhancements over the original:
    - DB-backed history (AIConversation) for auth users vs session for anon
    - Long-term user preference memory read from UserProfile.ai_preferences
    - Vision support: if image_data (base64) is provided, the user message
      becomes a multimodal content list understood by GPT-4o-mini's vision API
    - Sentiment detection: frustrated users get an empathy-first system prompt
    - Size recommendation: system prompt explicitly enables sizing help
    - Product metadata extraction: slugs mentioned in the reply are looked up
      and returned as structured data for rich card rendering in the chat UI
    - Falls back to keyword engine on any network/API failure
    """
    import urllib.request as urlreq
    import json as json_lib
    from django.conf import settings

    # ── Gather live context for the system prompt ─────────────
    cart = get_or_create_cart(request)
    cart_summary = (
        f"{cart.get_item_count()} item(s), total ${cart.get_total():.2f}"
        if cart.get_item_count() else "empty"
    )
    user_name = request.user.first_name if request.user.is_authenticated else "guest"
    is_logged_in = request.user.is_authenticated

    # Popular products — give the AI real catalogue awareness
    recent_products = list(
        Product.objects.filter(is_active=True, is_approved=True)
        .order_by('-views_count')[:10]
        .values('name', 'price', 'sale_price', 'slug', 'category__name', 'brand__name', 'color', 'size')
    )
    products_ctx = '; '.join([
        f"{p['name']} (${p['sale_price'] or p['price']}, {p['category__name']}"
        f"{', ' + p['brand__name'] if p['brand__name'] else ''}) → /products/{p['slug']}/"
        for p in recent_products
    ])

    # Active sale items
    sale_products = list(
        Product.objects.filter(is_active=True, is_approved=True, sale_price__isnull=False)
        .order_by('?')[:4]
        .values('name', 'price', 'sale_price', 'slug')
    )
    sales_ctx = '; '.join([
        f"{p['name']} was ${p['price']} now ${p['sale_price']}"
        for p in sale_products
    ]) or "None currently"

    # Order history
    orders_ctx = "Not logged in"
    if is_logged_in:
        recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:3]
        orders_ctx = '; '.join([
            f"#{o.order_number} ({o.get_status_display()}, ${o.total_amount})"
            for o in recent_orders
        ]) if recent_orders.exists() else "No orders yet"

    # Long-term preference memory — accumulated across sessions
    prefs_ctx = ""
    if is_logged_in:
        try:
            prefs = request.user.profile.ai_preferences or {}
            if prefs:
                prefs_ctx = f"\nUSER PREFERENCES (remembered from previous conversations): {json_lib.dumps(prefs)}"
        except UserProfile.DoesNotExist:
            pass

    # Sentiment instruction — added when frustration is detected
    frustrated = frontend_frustrated or _is_frustrated(_get_conversation_history(request))
    sentiment_instruction = (
        "\n\nSENTIMENT ALERT: The user seems frustrated. Lead with genuine empathy first. "
        "Acknowledge their frustration directly before helping. Offer: 'Would you like me to "
        "escalate this to our support team?' as a final option."
    ) if frustrated else ""

    system_prompt = (
        f"You are TrendMart AI — an intelligent, friendly, and highly knowledgeable shopping assistant "
        f"for TrendMart, a modern e-commerce platform owned by George Papasotiriou.\n\n"
        f"USER CONTEXT:\n"
        f"- Name: {user_name} | Logged in: {is_logged_in}\n"
        f"- Cart: {cart_summary}\n"
        f"- Recent orders: {orders_ctx}"
        f"{prefs_ctx}\n\n"
        f"LIVE CATALOGUE (most popular products):\n{products_ctx}\n\n"
        f"CURRENT SALES:\n{sales_ctx}\n\n"
        f"YOUR CAPABILITIES:\n"
        f"- Find, recommend, and compare products from the TrendMart catalogue\n"
        f"- Help with orders, returns, wishlist, account settings\n"
        f"- Shipping: standard 3–5 days, express 1–2 days, free over $50. Returns: 30 days.\n"
        f"- SIZE RECOMMENDATIONS: Ask for the user's height, weight, and body measurements "
        f"  to recommend clothing/shoe sizes. Use standard EU/UK/US size charts.\n"
        f"- Give personalised recommendations based on stated preferences and conversation history\n"
        f"- If user uploads an image, identify the product category/type and search the catalogue\n\n"
        f"FORMATTING RULES:\n"
        f"- Product references: 🔗[Product Name — $price](/products/product-slug/)\n"
        f"- Use **bold** for key terms, bullet lists for multiple items\n"
        f"- Keep responses under 280 words but thorough\n"
        f"- Always end with a helpful follow-up question or next-step suggestion\n"
        f"- Never invent products not in the catalogue — offer to search instead\n"
        f"- Remember preferences the user shares (sizes, brands, budget) for future replies\n\n"
        f"PERSONALITY: Warm, enthusiastic, expert — like a knowledgeable friend who loves shopping. "
        f"Use emojis sparingly. Be honest about limitations."
        f"{sentiment_instruction}"
    )

    # ── Load conversation history (DB for auth, session for anon) ─────────────
    history = _get_conversation_history(request)

    # ── Build user message content (text or multimodal with image) ────────────
    if image_data:
        # Vision request — the user uploaded an image; ask AI to identify and search
        user_content = [
            {"type": "text", "text": user_msg or "What product is this? Please identify it and find similar items in the TrendMart catalogue."},
            {"type": "image_url", "image_url": {"url": image_data}},
        ]
        # For history storage we keep only the text part
        user_history_content = user_msg or "[Image uploaded for visual search]"
    else:
        user_content = user_msg
        user_history_content = user_msg

    # Build full messages list: system + history (without new msg) + new user msg
    messages_payload = [{'role': 'system', 'content': system_prompt}]
    messages_payload += history  # already trimmed in _get_conversation_history
    messages_payload.append({'role': 'user', 'content': user_content})

    payload = {
        'model': getattr(settings, 'OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
        'messages': messages_payload,
        'max_tokens': 450,
        'temperature': 0.72,
    }

    try:
        req = urlreq.Request(
            'https://openrouter.ai/api/v1/chat/completions',
            data=json_lib.dumps(payload).encode(),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://trendmart.com',
                'X-Title': 'TrendMart AI Assistant',
            },
            method='POST'
        )
        with urlreq.urlopen(req, timeout=15) as resp:
            result = json_lib.loads(resp.read().decode())
            ai_reply = result['choices'][0]['message']['content']

        # ── Extract product metadata from the reply for rich cards ────────────
        # Find every /products/<slug>/ URL referenced in the AI reply and fetch
        # basic metadata so the frontend can render mini product cards.
        import re as _re
        slug_pattern = _re.compile(r'/products/([a-z0-9\-]+)/')
        mentioned_slugs = list(dict.fromkeys(slug_pattern.findall(ai_reply)))[:5]
        products_meta = []
        if mentioned_slugs:
            from .templatetags.shop_tags import product_image as _pi
            for slug in mentioned_slugs:
                p = Product.objects.filter(slug=slug, is_active=True, is_approved=True).first()
                if p:
                    products_meta.append({
                        'slug': p.slug,
                        'name': p.name,
                        'price': str(p.get_effective_price()),
                        'original_price': str(p.price) if p.sale_price else '',
                        'rating': float(p.get_avg_rating()),
                        'rating_count': p.get_rating_count(),
                        'image': _pi(p, 200, 200),
                        'url': f'/products/{p.slug}/',
                        'category': p.category.name,
                        'brand': p.brand.name if p.brand else '',
                    })

        return ai_reply, products_meta

    except Exception:
        # API failure — use keyword-based fallback
        fallback = _ai_response(request, user_msg.lower() if user_msg else 'hello')
        return fallback, []


# ── AI Natural-Language Search helper ─────────────────────────────────────────
def _parse_nl_query(query, api_key):
    """
    Calls OpenRouter to parse a plain-English shopping query into structured
    filter fields.  Returns a dict with any subset of:
      category, brand, min_price, max_price, color, size, keywords, summary
    Used by the /ai/search/ page to convert "I need running shoes under $100
    in blue, size 10" → {'category':'Shoes','max_price':100,'color':'blue','size':'10'}
    On any failure, returns a basic keyword-split dict so search still works.
    """
    import urllib.request as urlreq
    import json as json_lib
    from django.conf import settings

    parse_prompt = (
        'You are a shopping query parser. Parse the user shopping query and return ONLY a JSON object. '
        'Include only fields that are clearly specified. Available fields:\n'
        '{"category":"string","brand":"string","min_price":number,"max_price":number,'
        '"color":"string","size":"string","keywords":["string"],'
        '"summary":"friendly one-sentence description of the search"}\n'
        'Return ONLY valid JSON. No explanation, no markdown.'
    )
    payload = {
        'model': getattr(settings, 'OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
        'messages': [
            {'role': 'system', 'content': parse_prompt},
            {'role': 'user', 'content': query},
        ],
        'max_tokens': 220,
        'temperature': 0.1,
    }
    try:
        req = urlreq.Request(
            'https://openrouter.ai/api/v1/chat/completions',
            data=json_lib.dumps(payload).encode(),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://trendmart.com',
                'X-Title': 'TrendMart AI Search',
            },
            method='POST'
        )
        with urlreq.urlopen(req, timeout=10) as resp:
            result = json_lib.loads(resp.read().decode())
            content = result['choices'][0]['message']['content'].strip()
            # Strip any accidental markdown fences
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            return json_lib.loads(content.strip())
    except Exception:
        return {'keywords': query.split(), 'summary': f'Results for: {query}'}


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


# ─── AI Natural-Language Search Page ──────────────────────────────────────────

def ai_search(request):
    """
    Dedicated AI-powered natural-language product search at /ai/search/.
    The user types a plain-English shopping request such as:
        "I need a gift for my 8-year-old who loves dinosaurs, budget $30"
        "Blue running shoes for men, size 10, under $120"
    OpenRouter parses the query into structured filters which are then applied
    to the Product queryset and the results rendered as a product grid.
    Falls back gracefully to keyword search if the API is unavailable.
    """
    from django.conf import settings
    import json as _json

    query = request.GET.get('q', '').strip()
    results = Product.objects.none()
    ai_summary = ''
    interpreted = {}

    if query:
        api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
        if api_key:
            interpreted = _parse_nl_query(query, api_key)
        else:
            interpreted = {'keywords': query.split(), 'summary': f'Results for: {query}'}

        ai_summary = interpreted.get('summary', '')

        # Build queryset from extracted filters
        products = Product.objects.filter(is_active=True, is_approved=True).select_related('brand', 'category')

        if interpreted.get('category'):
            products = products.filter(category__name__icontains=interpreted['category'])
        if interpreted.get('brand'):
            products = products.filter(brand__name__icontains=interpreted['brand'])
        if interpreted.get('max_price'):
            try:
                products = products.filter(price__lte=float(interpreted['max_price']))
            except (ValueError, TypeError):
                pass
        if interpreted.get('min_price'):
            try:
                products = products.filter(price__gte=float(interpreted['min_price']))
            except (ValueError, TypeError):
                pass
        if interpreted.get('color'):
            products = products.filter(color__icontains=interpreted['color'])
        if interpreted.get('size'):
            products = products.filter(size__icontains=str(interpreted['size']))

        # Apply keyword search across name/description/tags
        keywords = interpreted.get('keywords', [])
        if keywords:
            kw_q = Q()
            for kw in keywords:
                if len(kw) > 2:  # skip short stop words
                    kw_q |= Q(name__icontains=kw) | Q(description__icontains=kw) | Q(tags__icontains=kw)
            if kw_q:
                products = products.filter(kw_q)

        results = products.order_by('-views_count')[:24]

    return render(request, 'shop/ai_search.html', {
        'query': query,
        'results': results,
        'ai_summary': ai_summary,
        'interpreted': interpreted,
        'result_count': results.count() if query else 0,
        'root_categories': Category.objects.filter(parent=None, is_active=True),
    })


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


# =============================================================================
# ─── NEW FEATURE VIEWS (Session 8 additions) ──────────────────────────────────
# All views below implement the 112-point improvement roadmap.
# Author: George Papasotiriou — TrendMart, March 2026
# =============================================================================

# ── Utility: get client IP ────────────────────────────────────────────────────
def _get_client_ip(request):
    """Extract the real client IP, handling reverse-proxy X-Forwarded-For headers."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ── Utility: audit log helper ─────────────────────────────────────────────────
def _audit(request, action, model_name='', object_id='', detail=''):
    """Create an AuditLog row. Called from admin/retailer destructive actions."""
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        detail=detail,
        ip_address=_get_client_ip(request),
    )


# ── Utility: send notification ────────────────────────────────────────────────
def _notify(user, notification_type, title, message, link=''):
    """Create a Notification row and increment the user's unread count."""
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def notification_list(request):
    """
    Displays all notifications for the logged-in user and marks them all as read.
    A bell icon in the nav shows the unread count via context processor.
    """
    notifications = Notification.objects.filter(user=request.user)
    # Mark all unread as read when the user opens the notification centre
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'shop/notifications.html', {'notifications': notifications})


def notifications_count(request):
    """AJAX endpoint — returns unread notification count for the nav bell."""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


# ─────────────────────────────────────────────────────────────────────────────
# LOYALTY POINTS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def loyalty_dashboard(request):
    """
    Shows the user's loyalty point balance, transaction history, and how
    many points they need for the next reward tier.
    """
    loyalty, _ = LoyaltyPoints.objects.get_or_create(user=request.user)
    transactions = LoyaltyTransaction.objects.filter(user=request.user)[:20]
    # Define reward tiers (points needed → reward description)
    tiers = [
        {'name': 'Bronze', 'points': 0,    'icon': '🥉', 'benefit': '5% off any order'},
        {'name': 'Silver', 'points': 500,  'icon': '🥈', 'benefit': '10% off + free shipping'},
        {'name': 'Gold',   'points': 1500, 'icon': '🥇', 'benefit': '15% off + priority support'},
        {'name': 'Platinum','points': 5000,'icon': '💎', 'benefit': '20% off + exclusive deals'},
    ]
    current_tier = tiers[0]
    next_tier = None
    for i, tier in enumerate(tiers):
        if loyalty.points >= tier['points']:
            current_tier = tier
            next_tier = tiers[i + 1] if i + 1 < len(tiers) else None
    context = {
        'loyalty': loyalty,
        'transactions': transactions,
        'current_tier': current_tier,
        'next_tier': next_tier,
        'tiers': tiers,
    }
    return render(request, 'shop/loyalty.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# PROMO CODES
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
def apply_promo_code(request):
    """
    AJAX view — validates a promo code against the current cart total.
    Returns discount amount and new total on success, or an error message.
    """
    import json as _json
    try:
        data = _json.loads(request.body)
    except Exception:
        data = {}
    code_str = data.get('code', '').strip().upper()
    if not code_str:
        return JsonResponse({'error': 'Please enter a promo code.'}, status=400)

    try:
        promo = PromoCode.objects.get(code=code_str)
    except PromoCode.DoesNotExist:
        return JsonResponse({'error': 'Invalid promo code.'}, status=400)

    if not promo.is_valid():
        return JsonResponse({'error': 'This promo code has expired or is no longer valid.'}, status=400)

    cart = get_or_create_cart(request)
    cart_total = float(cart.get_total())
    discount = float(promo.calculate_discount(cart_total))

    if discount == 0:
        return JsonResponse({'error': f'Minimum order of ${promo.minimum_order} required for this code.'}, status=400)

    # Store in session so checkout can apply it
    request.session['promo_code'] = code_str
    request.session['promo_discount'] = discount
    request.session.modified = True

    return JsonResponse({
        'success': True,
        'code': code_str,
        'discount': discount,
        'new_total': round(cart_total - discount, 2),
        'message': f'🎉 Code "{code_str}" applied — ${discount:.2f} off!',
    })


# ─────────────────────────────────────────────────────────────────────────────
# RETAILER STOREFRONT
# ─────────────────────────────────────────────────────────────────────────────

def retailer_storefront(request, username):
    """
    Public storefront page for an approved retailer.
    Shows their profile, active products, and average store rating.
    URL: /store/<username>/
    """
    retailer_user = get_object_or_404(User, username=username)
    # Only show storefronts for approved retailers
    try:
        retailer_profile = retailer_user.retailer_profile
        if not retailer_profile.is_approved:
            from django.http import Http404
            raise Http404
    except RetailerProfile.DoesNotExist:
        from django.http import Http404
        raise Http404

    products = Product.objects.filter(
        retailer=retailer_user, is_active=True, is_approved=True
    ).select_related('category', 'brand').prefetch_related('ratings', 'images')

    # Compute average store rating across all the retailer's products
    avg_store_rating = products.aggregate(avg=Avg('ratings__rating'))['avg'] or 0

    context = {
        'retailer_user': retailer_user,
        'retailer_profile': retailer_profile,
        'products': products,
        'product_count': products.count(),
        'avg_store_rating': round(avg_store_rating, 1),
    }
    return render(request, 'shop/storefront.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# RETAILER ANALYTICS DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@retailer_required
def retailer_analytics(request):
    """
    Chart.js analytics dashboard scoped to the logged-in retailer's products.
    Shows: revenue trend (last 30 days), top products by revenue, order count.
    """
    from datetime import timedelta

    my_products = Product.objects.filter(retailer=request.user)
    product_ids = list(my_products.values_list('id', flat=True))

    # Revenue trend: daily revenue for past 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_revenue = (
        OrderItem.objects
        .filter(product__in=product_ids, order__created_at__gte=thirty_days_ago)
        .extra(select={'day': "date(order__created_at)"})  # SQLite date extract
        .values('day')
        .annotate(revenue=Sum(F('product_price') * F('quantity')))
        .order_by('day')
    )

    # Top 5 products by total revenue
    top_products = (
        OrderItem.objects
        .filter(product__in=product_ids)
        .values('product_name')
        .annotate(revenue=Sum(F('product_price') * F('quantity')), units=Sum('quantity'))
        .order_by('-revenue')[:5]
    )

    # Total stats
    total_revenue = OrderItem.objects.filter(product__in=product_ids).aggregate(
        total=Sum(F('product_price') * F('quantity'))
    )['total'] or 0

    total_orders = Order.objects.filter(items__product__in=product_ids).distinct().count()

    context = {
        'my_products': my_products,
        'daily_revenue': list(daily_revenue),
        'top_products': list(top_products),
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_products': my_products.count(),
    }
    return render(request, 'shop/dashboard/retailer_analytics.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# BULK PRODUCT CSV IMPORT
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@retailer_required
def retailer_csv_import(request):
    """
    Allows retailers to upload a CSV file to bulk-create products.
    Required CSV columns: name, price, description, category_name, stock
    Optional: brand_name, color, size, tags, short_description
    """
    import csv
    import io as _io

    results = []
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(_io.StringIO(decoded))
        created = 0
        errors = 0
        for row_num, row in enumerate(reader, start=2):
            try:
                # Resolve or create category
                cat_name = row.get('category_name', '').strip()
                if not cat_name:
                    results.append(f"Row {row_num}: Missing category_name — skipped.")
                    errors += 1
                    continue
                category, _ = Category.objects.get_or_create(name=cat_name)

                # Optionally resolve brand
                brand = None
                brand_name = row.get('brand_name', '').strip()
                if brand_name:
                    brand, _ = Brand.objects.get_or_create(name=brand_name)

                price_str = row.get('price', '0').strip()
                try:
                    price = float(price_str)
                except ValueError:
                    results.append(f"Row {row_num}: Invalid price '{price_str}' — skipped.")
                    errors += 1
                    continue

                product = Product(
                    retailer=request.user,
                    category=category,
                    brand=brand,
                    name=row.get('name', '').strip(),
                    description=row.get('description', '').strip(),
                    short_description=row.get('short_description', '').strip(),
                    price=price,
                    stock=int(row.get('stock', 0)),
                    color=row.get('color', '').strip(),
                    size=row.get('size', '').strip(),
                    tags=row.get('tags', '').strip(),
                    is_approved=False,  # Always requires admin approval
                )
                product.save()
                created += 1
                results.append(f"Row {row_num}: ✅ Created '{product.name}'")
            except Exception as exc:
                results.append(f"Row {row_num}: ❌ Error — {exc}")
                errors += 1

        _audit(request, f'CSV import: {created} products created, {errors} errors', 'Product')
        messages.success(request, f"Import complete: {created} products created, {errors} errors.")

    return render(request, 'shop/dashboard/csv_import.html', {'results': results})


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT Q&A
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def ask_question(request, slug):
    """Submit a new question on a product page (AJAX)."""
    import json as _json
    product = get_object_or_404(Product, slug=slug, is_active=True)
    try:
        data = _json.loads(request.body)
    except Exception:
        data = {}
    question_text = data.get('question', '').strip()
    if not question_text:
        return JsonResponse({'error': 'Question cannot be empty.'}, status=400)
    q = ProductQuestion.objects.create(product=product, user=request.user, question=question_text)
    return JsonResponse({
        'success': True,
        'question': q.question,
        'user': request.user.get_full_name() or request.user.username,
        'created_at': q.created_at.strftime('%b %d, %Y'),
    })


@login_required
@require_POST
def answer_question(request, question_id):
    """Submit an answer to a product question (AJAX)."""
    import json as _json
    question = get_object_or_404(ProductQuestion, pk=question_id, is_approved=True)
    try:
        data = _json.loads(request.body)
    except Exception:
        data = {}
    answer_text = data.get('answer', '').strip()
    if not answer_text:
        return JsonResponse({'error': 'Answer cannot be empty.'}, status=400)

    # Check if the answerer is the product's retailer
    is_retailer = (question.product.retailer == request.user)
    ans = ProductAnswer.objects.create(
        question=question,
        user=request.user,
        answer=answer_text,
        is_retailer_answer=is_retailer,
    )
    return JsonResponse({
        'success': True,
        'answer': ans.answer,
        'user': request.user.get_full_name() or request.user.username,
        'is_retailer': is_retailer,
        'created_at': ans.created_at.strftime('%b %d, %Y'),
    })


# ─────────────────────────────────────────────────────────────────────────────
# REVIEW REPLY (retailer replies to a review)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def reply_to_review(request, review_id):
    """Retailer posts a public reply to a customer review on their product."""
    import json as _json
    review = get_object_or_404(ProductRating, pk=review_id)
    # Only the product's retailer may reply
    if review.product.retailer != request.user and not request.user.is_staff:
        return JsonResponse({'error': 'Not authorised.'}, status=403)
    try:
        data = _json.loads(request.body)
    except Exception:
        data = {}
    reply_text = data.get('reply', '').strip()
    if not reply_text:
        return JsonResponse({'error': 'Reply cannot be empty.'}, status=400)

    reply_obj, created = ReviewReply.objects.update_or_create(
        review=review,
        defaults={'user': request.user, 'reply': reply_text},
    )
    # Notify the reviewer
    _notify(
        review.user, 'review_reply',
        f'{request.user.get_full_name() or request.user.username} replied to your review',
        reply_text[:120],
        link=f'/products/{review.product.slug}/',
    )
    return JsonResponse({'success': True, 'reply': reply_obj.reply, 'created': created})


# ─────────────────────────────────────────────────────────────────────────────
# WISHLIST SHARING
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def generate_wishlist_share(request):
    """Create or refresh the wishlist share token and return the shareable URL."""
    token_obj, _ = WishlistShareToken.objects.get_or_create(user=request.user)
    token_obj.is_active = True
    token_obj.save()
    share_url = request.build_absolute_uri(f'/wishlist/shared/{token_obj.token}/')
    return JsonResponse({'url': share_url})


def shared_wishlist(request, token):
    """
    Public read-only view of a user's wishlist accessed via their share token.
    No authentication required — anyone with the link can view the list.
    """
    token_obj = get_object_or_404(WishlistShareToken, token=token, is_active=True)
    wishlist_items = WishlistItem.objects.filter(
        user=token_obj.user
    ).select_related('product', 'product__category', 'product__brand')
    return render(request, 'shop/shared_wishlist.html', {
        'owner': token_obj.user,
        'wishlist_items': wishlist_items,
    })


# ─────────────────────────────────────────────────────────────────────────────
# STOCK NOTIFICATION
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
def notify_back_in_stock(request, slug):
    """
    Register the user's email to be notified when a product is back in stock.
    Works for both logged-in and anonymous users.
    """
    import json as _json
    product = get_object_or_404(Product, slug=slug)
    try:
        data = _json.loads(request.body)
    except Exception:
        data = {}

    email = data.get('email', '').strip()
    if request.user.is_authenticated:
        email = email or request.user.email

    if not email:
        return JsonResponse({'error': 'Please provide your email address.'}, status=400)

    _, created = StockNotification.objects.get_or_create(
        product=product,
        email=email,
        defaults={'user': request.user if request.user.is_authenticated else None},
    )
    if created:
        return JsonResponse({'success': True, 'message': f"We'll email {email} when this item is back in stock."})
    return JsonResponse({'success': True, 'message': "You're already on the notification list for this item."})


# ─────────────────────────────────────────────────────────────────────────────
# NEWSLETTER SUBSCRIPTION
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
def newsletter_subscribe(request):
    """
    AJAX view — adds an email address to the newsletter subscriber list.
    Responds with JSON for inline confirmation without page reload.
    """
    import json as _json
    try:
        data = _json.loads(request.body)
    except Exception:
        data = {}
    email = data.get('email', '').strip()
    name = data.get('name', '').strip()

    if not email or '@' not in email:
        return JsonResponse({'error': 'Please enter a valid email address.'}, status=400)

    _, created = NewsletterSubscriber.objects.get_or_create(
        email=email,
        defaults={'name': name, 'is_active': True},
    )
    if created:
        return JsonResponse({'success': True, 'message': "🎉 You're subscribed! Expect great deals in your inbox."})
    return JsonResponse({'success': True, 'message': "You're already subscribed — thanks!"})


# ─────────────────────────────────────────────────────────────────────────────
# COLLECTIONS / SHOP BY MOOD
# ─────────────────────────────────────────────────────────────────────────────

def collections_list(request):
    """
    The "Shop by Mood" landing page.
    Displays all active curated product collections (e.g. "Summer Essentials").
    """
    collections = Collection.objects.filter(is_active=True).prefetch_related('products')
    return render(request, 'shop/collections.html', {'collections': collections})


def collection_detail(request, slug):
    """
    Detail page for a single collection — shows all products tagged in it.
    Supports the same advanced filtering as the main product list.
    """
    collection = get_object_or_404(Collection, slug=slug, is_active=True)
    products = collection.products.filter(
        is_active=True, is_approved=True
    ).select_related('category', 'brand').prefetch_related('ratings', 'images')

    # Apply sorting
    sort = request.GET.get('sort', 'default')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'rating':
        products = products.annotate(avg_r=Avg('ratings__rating')).order_by('-avg_r')
    elif sort == 'newest':
        products = products.order_by('-created_at')

    return render(request, 'shop/collection_detail.html', {
        'collection': collection,
        'products': products,
        'product_count': products.count(),
        'current_sort': sort,
    })


# ─────────────────────────────────────────────────────────────────────────────
# REFERRAL SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def referral_dashboard(request):
    """
    Shows the logged-in user their unique referral link and a list of
    users they've referred, with bonus points earned from each referral.
    """
    referral_link = request.build_absolute_uri(f'/register/?ref={request.user.username}')
    referrals_made = Referral.objects.filter(referrer=request.user).select_related('referred')
    loyalty, _ = LoyaltyPoints.objects.get_or_create(user=request.user)
    return render(request, 'shop/referral.html', {
        'referral_link': referral_link,
        'referrals_made': referrals_made,
        'loyalty': loyalty,
    })


# ─────────────────────────────────────────────────────────────────────────────
# SAVED ADDRESSES
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def address_list(request):
    """View and add saved shipping addresses (max 5 per user)."""
    addresses = UserAddress.objects.filter(user=request.user)
    if request.method == 'POST':
        if addresses.count() >= 5:
            messages.error(request, 'You can save a maximum of 5 addresses.')
            return redirect('shop:address_list')
        label = request.POST.get('label', 'Home')
        full_name = request.POST.get('full_name', '').strip()
        address_text = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        country = request.POST.get('country', 'Greece').strip()
        postal_code = request.POST.get('postal_code', '').strip()
        phone = request.POST.get('phone', '').strip()
        is_default = 'is_default' in request.POST
        if is_default:
            addresses.update(is_default=False)
        UserAddress.objects.create(
            user=request.user, label=label, full_name=full_name,
            address=address_text, city=city, country=country,
            postal_code=postal_code, phone=phone, is_default=is_default,
        )
        messages.success(request, 'Address saved.')
        return redirect('shop:address_list')
    return render(request, 'shop/addresses.html', {'addresses': addresses})


@login_required
def address_delete(request, pk):
    """Delete a saved address (POST only)."""
    addr = get_object_or_404(UserAddress, pk=pk, user=request.user)
    if request.method == 'POST':
        addr.delete()
        messages.success(request, 'Address removed.')
    return redirect('shop:address_list')


# ─────────────────────────────────────────────────────────────────────────────
# AI — GENERATE PRODUCT DESCRIPTION
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@retailer_required
@require_POST
def ai_generate_description(request):
    """
    Retailer clicks "✨ Generate description" on the product form.
    Calls OpenRouter with product name + brand + category to auto-fill the description.
    """
    import json as _json, urllib.request as _urlreq
    from django.conf import settings as _settings
    try:
        data = _json.loads(request.body)
    except Exception:
        data = {}

    product_name = data.get('name', '').strip()
    brand = data.get('brand', '').strip()
    category = data.get('category', '').strip()
    color = data.get('color', '').strip()

    if not product_name:
        return JsonResponse({'error': 'Product name is required.'}, status=400)

    api_key = getattr(_settings, 'OPENROUTER_API_KEY', '')
    if not api_key:
        return JsonResponse({'error': 'AI service not configured.'}, status=503)

    prompt = (
        f"Write a compelling, SEO-friendly product description for an e-commerce listing. "
        f"Product: {product_name}. "
        f"{'Brand: ' + brand + '. ' if brand else ''}"
        f"{'Category: ' + category + '. ' if category else ''}"
        f"{'Colour: ' + color + '. ' if color else ''}"
        f"The description should be 80-120 words, highlight key benefits and features, "
        f"and use engaging language that converts browsers into buyers. "
        f"Do not include a title — just the description text."
    )

    payload = {
        'model': getattr(_settings, 'OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 200,
        'temperature': 0.8,
    }
    try:
        req = _urlreq.Request(
            'https://openrouter.ai/api/v1/chat/completions',
            data=_json.dumps(payload).encode(),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://trendmart.com',
                'X-Title': 'TrendMart Product Generator',
            },
            method='POST'
        )
        with _urlreq.urlopen(req, timeout=15) as resp:
            result = _json.loads(resp.read().decode())
            description = result['choices'][0]['message']['content'].strip()
        return JsonResponse({'description': description})
    except Exception as exc:
        return JsonResponse({'error': f'AI service error: {exc}'}, status=503)


# ─────────────────────────────────────────────────────────────────────────────
# SPIN-TO-WIN WHEEL (GDPR-friendly — one spin per day per user/session)
# ─────────────────────────────────────────────────────────────────────────────

def spin_wheel(request):
    """
    Renders the gamified daily spin-to-win page.
    GET: shows the wheel.
    POST: processes the spin — generates a promo code, records in session.
    """
    from datetime import date
    spin_key = 'last_spin_date'
    result = None
    already_spun = False

    if request.method == 'POST':
        last_spin = request.session.get(spin_key)
        today_str = str(date.today())

        if last_spin == today_str:
            already_spun = True
        else:
            import random
            prizes = [
                {'label': '5% OFF', 'code_prefix': 'SPIN5', 'discount_value': 5, 'discount_type': 'percentage'},
                {'label': '10% OFF', 'code_prefix': 'SPIN10', 'discount_value': 10, 'discount_type': 'percentage'},
                {'label': 'Free Shipping', 'code_prefix': 'SPINSHIP', 'discount_value': 0, 'discount_type': 'flat'},
                {'label': '$5 OFF', 'code_prefix': 'SPIN5D', 'discount_value': 5, 'discount_type': 'flat'},
                {'label': '15% OFF', 'code_prefix': 'SPIN15', 'discount_value': 15, 'discount_type': 'percentage'},
                {'label': '2x Points', 'code_prefix': 'SPINPTS', 'discount_value': 0, 'discount_type': 'flat'},
                {'label': '$10 OFF', 'code_prefix': 'SPIN10D', 'discount_value': 10, 'discount_type': 'flat'},
                {'label': 'Try Again', 'code_prefix': None, 'discount_value': 0, 'discount_type': 'flat'},
            ]
            prize = random.choice(prizes)
            request.session[spin_key] = today_str
            request.session.modified = True

            promo_code_str = None
            if prize['code_prefix'] and prize['discount_value'] > 0:
                import uuid as _uuid
                promo_code_str = f"{prize['code_prefix']}-{str(_uuid.uuid4()).upper()[:6]}"
                from datetime import timedelta
                PromoCode.objects.create(
                    code=promo_code_str,
                    discount_type=prize['discount_type'],
                    discount_value=prize['discount_value'],
                    max_uses=1,
                    is_active=True,
                    expires_at=timezone.now() + timedelta(hours=24),
                    created_by=request.user if request.user.is_authenticated else None,
                )
                if request.user.is_authenticated:
                    _notify(request.user, 'loyalty', f"You won: {prize['label']}!",
                            f"Your promo code is {promo_code_str} — valid for 24 hours.", link='/cart/')

            result = {'label': prize['label'], 'code': promo_code_str}

    return render(request, 'shop/spin_wheel.html', {
        'result': result,
        'already_spun': already_spun,
    })


# ─────────────────────────────────────────────────────────────────────────────
# SAVE FOR LATER
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def save_for_later(request, item_id):
    """
    Moves a cart item to the user's wishlist and removes it from the cart.
    Called via AJAX from the cart page.
    """
    cart_item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    product = cart_item.product
    # Add to wishlist (idempotent — ignores if already wishlisted)
    WishlistItem.objects.get_or_create(user=request.user, product=product)
    cart_item.delete()
    cart = get_or_create_cart(request)
    return JsonResponse({
        'success': True,
        'message': f'"{product.name}" saved to wishlist.',
        'cart_count': cart.get_item_count(),
        'cart_total': float(cart.get_total()),
    })


# ─────────────────────────────────────────────────────────────────────────────
# SURPRISE ME
# ─────────────────────────────────────────────────────────────────────────────

def surprise_me(request):
    """
    Redirects the user to a random product from their most-browsed category.
    Falls back to a completely random active product if no history exists.
    """
    product = None
    if request.user.is_authenticated:
        # Find the user's most-viewed category
        top_category = (
            ViewedProduct.objects.filter(user=request.user)
            .values('product__category')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')
            .first()
        )
        if top_category:
            category_id = top_category['product__category']
            product = (
                Product.objects.filter(category_id=category_id, is_active=True, is_approved=True)
                .order_by('?')
                .first()
            )
    if not product:
        product = Product.objects.filter(is_active=True, is_approved=True).order_by('?').first()

    if product:
        return redirect('shop:product_detail', slug=product.slug)
    return redirect('shop:product_list')


# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNT DELETION (GDPR)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def delete_account(request):
    """
    GDPR-compliant account deletion.
    POST: anonymises the user's personal data and deactivates the account.
    The user is logged out immediately after deletion.
    GET: shows a confirmation page.
    """
    if request.method == 'POST':
        user = request.user
        # Anonymise personal data (GDPR Article 17)
        anon_name = f"deleted_{user.id}"
        user.username = anon_name
        user.email = f"{anon_name}@deleted.trendmart.com"
        user.first_name = ''
        user.last_name = ''
        user.is_active = False
        user.save()
        try:
            profile = user.profile
            profile.phone = ''
            profile.address = ''
            profile.city = ''
            profile.country = ''
            profile.postal_code = ''
            profile.bio = ''
            profile.date_of_birth = None
            profile.avatar = None
            profile.ai_preferences = {}
            profile.save()
        except UserProfile.DoesNotExist:
            pass
        logout(request)
        messages.success(request, "Your account has been permanently deleted. We're sorry to see you go.")
        return redirect('shop:home')
    return render(request, 'shop/delete_account.html')


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN: ZERO-RESULT SEARCHES REPORT
# ─────────────────────────────────────────────────────────────────────────────

@admin_required
def admin_search_logs(request):
    """Admin view: shows searches with 0 results to reveal catalogue gaps."""
    zero_results = SearchLog.objects.filter(result_count=0).order_by('-created_at')[:100]
    # Group by query term and count frequency
    from django.db.models import Count as _Count
    grouped = (
        SearchLog.objects.filter(result_count=0)
        .values('query')
        .annotate(count=_Count('id'))
        .order_by('-count')[:30]
    )
    return render(request, 'shop/admin_panel/search_logs.html', {
        'zero_results': zero_results,
        'grouped': grouped,
    })


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN: AUDIT LOG VIEW
# ─────────────────────────────────────────────────────────────────────────────

@admin_required
def admin_audit_log(request):
    """Admin view: shows recent platform actions for accountability."""
    logs = AuditLog.objects.select_related('user').all()[:200]
    return render(request, 'shop/admin_panel/audit_log.html', {'logs': logs})


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN: PRODUCT PERFORMANCE TABLE
# ─────────────────────────────────────────────────────────────────────────────

@admin_required
def admin_product_performance(request):
    """
    Admin analytics: products ranked by views, revenue, and conversion rate.
    Helps identify top performers and slow-moving inventory.
    """
    products = Product.objects.filter(is_active=True).annotate(
        total_revenue=Sum(F('order_items__product_price') * F('order_items__quantity')),
        total_units=Sum('order_items__quantity'),
        avg_rating=Avg('ratings__rating'),
    ).order_by('-views_count')[:50]

    return render(request, 'shop/admin_panel/product_performance.html', {'products': products})


# ─────────────────────────────────────────────────────────────────────────────
# MINI CART DATA (AJAX)
# ─────────────────────────────────────────────────────────────────────────────

def mini_cart_data(request):
    """
    AJAX endpoint — returns current cart items as JSON for the slide-in drawer.
    Called after every add-to-cart action to refresh the mini cart contents.
    """
    cart = get_or_create_cart(request)
    items = []
    for item in cart.items.select_related('product').all():
        from .templatetags.shop_tags import product_image as _pimg
        items.append({
            'id': item.id,
            'name': item.product.name,
            'price': float(item.product.get_effective_price()),
            'quantity': item.quantity,
            'subtotal': float(item.get_subtotal()),
            'image': _pimg(item.product, 80, 80),
            'slug': item.product.slug,
            'size': item.size,
        })
    return JsonResponse({
        'items': items,
        'total': float(cart.get_total()),
        'count': cart.get_item_count(),
    })
