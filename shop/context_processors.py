from .models import Cart, Category


def cart_context(request):
    cart_count = 0
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key, user=None).first() if session_key else None
        if cart:
            cart_count = cart.get_item_count()
    except Exception:
        pass
    return {'cart_count': cart_count}


def site_context(request):
    root_categories = Category.objects.filter(parent=None, is_active=True).prefetch_related('children')
    return {
        'site_name': 'TrendMart',
        'site_tagline': 'Shop the Trend, Live the Style',
        'root_categories': root_categories,
    }
