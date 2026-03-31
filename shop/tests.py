"""
TrendMart — Automated Test Suite
Author: George Papasotiriou
Coverage: Models, Views (status codes + context), Cart logic, Recommender, AI assistant
Run with: pytest   OR   python manage.py test shop
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from .models import (
    UserProfile, Category, Brand, Product,
    Cart, CartItem, Order, OrderItem,
    WishlistItem, ProductRating,
)


# ─── Fixtures / Helpers ───────────────────────────────────────────────────────

def make_user(username='testuser', password='testpass123', role='customer'):
    user = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': role})
    profile.role = role
    profile.save()
    return user


def make_category(name='Electronics'):
    return Category.objects.get_or_create(name=name)[0]


def make_brand(name='TestBrand'):
    return Brand.objects.get_or_create(name=name)[0]


def make_product(name='Test Product', price='99.99', stock=10, **kwargs):
    cat = make_category()
    brand = make_brand()
    user, _ = User.objects.get_or_create(username='retailer_seed', defaults={'email': 'retailer_seed@test.com'})
    user.set_password('testpass123')
    user.save()
    UserProfile.objects.get_or_create(user=user, defaults={'role': 'retailer'})
    return Product.objects.create(
        name=name,
        price=Decimal(price),
        stock=stock,
        category=cat,
        brand=brand,
        retailer=user,
        description='A great test product.',
        is_approved=True,
        is_active=True,
        **kwargs,
    )


# ─── Model Tests ──────────────────────────────────────────────────────────────

class TestProductModel(TestCase):

    def setUp(self):
        self.product = make_product(price='100.00', sale_price=None)

    def test_str_returns_name(self):
        self.assertEqual(str(self.product), self.product.name)

    def test_slug_auto_generated(self):
        self.assertTrue(self.product.slug)

    def test_sku_auto_generated(self):
        self.assertTrue(len(self.product.sku) > 0)

    def test_effective_price_without_sale(self):
        self.assertEqual(self.product.get_effective_price(), Decimal('100.00'))

    def test_effective_price_with_sale(self):
        self.product.sale_price = Decimal('75.00')
        self.product.save()
        self.assertEqual(self.product.get_effective_price(), Decimal('75.00'))

    def test_is_on_sale_false_when_no_sale_price(self):
        self.product.sale_price = None
        self.assertFalse(self.product.is_on_sale())

    def test_is_on_sale_true_when_sale_price_lower(self):
        self.product.sale_price = Decimal('80.00')
        self.product.price = Decimal('100.00')
        self.assertTrue(self.product.is_on_sale())

    def test_get_discount_percentage(self):
        self.product.price = Decimal('100.00')
        self.product.sale_price = Decimal('75.00')
        self.assertEqual(self.product.get_discount_percentage(), 25)

    def test_get_discount_percentage_no_sale(self):
        self.product.sale_price = None
        self.assertEqual(self.product.get_discount_percentage(), 0)

    def test_is_in_stock_true(self):
        self.assertTrue(self.product.is_in_stock())

    def test_is_in_stock_false(self):
        self.product.stock = 0
        self.assertFalse(self.product.is_in_stock())

    def test_get_avg_rating_no_reviews(self):
        self.assertEqual(self.product.get_avg_rating(), 0)

    def test_get_tags_list(self):
        self.product.tags = 'sports, casual, summer'
        self.assertEqual(self.product.get_tags_list(), ['sports', 'casual', 'summer'])

    def test_get_tags_list_empty(self):
        self.product.tags = ''
        self.assertEqual(self.product.get_tags_list(), [])

    def test_unique_slug_for_duplicate_names(self):
        p2 = make_product(name='Test Product')
        self.assertNotEqual(self.product.slug, p2.slug)


class TestUserProfileModel(TestCase):

    def setUp(self):
        self.user = make_user()
        self.profile = self.user.profile

    def test_str(self):
        self.assertIn(self.user.username, str(self.profile))

    def test_is_retailer_false_for_customer(self):
        self.assertFalse(self.profile.is_retailer())

    def test_is_retailer_true(self):
        self.profile.role = 'retailer'
        self.assertTrue(self.profile.is_retailer())

    def test_is_admin_role_false_for_customer(self):
        self.assertFalse(self.profile.is_admin_role())

    def test_is_admin_role_true_for_staff(self):
        self.user.is_staff = True
        self.user.save()
        self.assertTrue(self.profile.is_admin_role())


class TestCartModel(TestCase):

    def setUp(self):
        self.user = make_user(username='cartuser')
        self.product = make_product(price='50.00')
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_str(self):
        self.assertIn('cartuser', str(self.cart))

    def test_get_total_empty_cart(self):
        self.assertEqual(self.cart.get_total(), 0)

    def test_get_total_with_items(self):
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.assertEqual(self.cart.get_total(), Decimal('100.00'))

    def test_get_item_count(self):
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=3)
        self.assertEqual(self.cart.get_item_count(), 3)


class TestOrderModel(TestCase):

    def test_order_number_auto_generated(self):
        user = make_user(username='orderuser')
        order = Order.objects.create(
            user=user, full_name='Test User', email='test@test.com',
            address='123 Street', total_amount=Decimal('99.00'),
        )
        self.assertTrue(order.order_number.startswith('TM'))
        self.assertEqual(len(order.order_number), 10)

    def test_order_str(self):
        user = make_user(username='orderuser2')
        order = Order.objects.create(
            user=user, full_name='Test User 2', email='test2@test.com',
            address='456 Ave', total_amount=Decimal('50.00'),
        )
        self.assertIn(order.order_number, str(order))


# ─── View Tests ───────────────────────────────────────────────────────────────

class TestPublicViews(TestCase):

    def setUp(self):
        self.client = Client()
        self.product = make_product()

    def test_homepage_200(self):
        response = self.client.get(reverse('shop:home'))
        self.assertEqual(response.status_code, 200)

    def test_product_list_200(self):
        response = self.client.get(reverse('shop:product_list'))
        self.assertEqual(response.status_code, 200)

    def test_product_detail_200(self):
        response = self.client.get(reverse('shop:product_detail', kwargs={'slug': self.product.slug}))
        self.assertEqual(response.status_code, 200)

    def test_product_detail_404_for_missing_slug(self):
        response = self.client.get(reverse('shop:product_detail', kwargs={'slug': 'nonexistent-slug'}))
        self.assertEqual(response.status_code, 404)

    def test_faq_page_200(self):
        response = self.client.get(reverse('shop:faq'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_200(self):
        response = self.client.get(reverse('shop:login'))
        self.assertEqual(response.status_code, 200)

    def test_register_page_200(self):
        response = self.client.get(reverse('shop:register'))
        self.assertEqual(response.status_code, 200)

    def test_health_check_200(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)

    def test_search_returns_results(self):
        response = self.client.get(reverse('shop:product_list') + '?q=Test')
        self.assertEqual(response.status_code, 200)

    def test_product_detail_context_has_product(self):
        response = self.client.get(reverse('shop:product_detail', kwargs={'slug': self.product.slug}))
        self.assertIn('product', response.context)
        self.assertEqual(response.context['product'], self.product)


class TestAuthViews(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user(username='authtest', password='authpass123')

    def test_login_valid_credentials(self):
        response = self.client.post(reverse('shop:login'), {
            'username': 'authtest', 'password': 'authpass123'
        })
        self.assertIn(response.status_code, [200, 302])

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('shop:dashboard'))
        self.assertIn(response.status_code, [302, 301])

    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username='authtest', password='authpass123')
        response = self.client.get(reverse('shop:dashboard'))
        self.assertEqual(response.status_code, 200)


class TestCartViews(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user(username='cartviewuser', password='pass123')
        self.product = make_product()
        self.client.login(username='cartviewuser', password='pass123')

    def test_add_to_cart_ajax(self):
        response = self.client.post(
            reverse('shop:add_to_cart'),
            {'product_id': self.product.id, 'quantity': 1},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertIn(response.status_code, [200, 302])

    def test_cart_page_200(self):
        response = self.client.get(reverse('shop:cart'))
        self.assertEqual(response.status_code, 200)

    def test_mini_cart_200(self):
        response = self.client.get(reverse('shop:mini_cart_data'))
        self.assertEqual(response.status_code, 200)


class TestWishlistViews(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user(username='wishlistuser', password='wish123')
        self.product = make_product()
        self.client.login(username='wishlistuser', password='wish123')

    def test_wishlist_page_200(self):
        response = self.client.get(reverse('shop:wishlist'))
        self.assertEqual(response.status_code, 200)

    def test_toggle_wishlist(self):
        response = self.client.post(
            reverse('shop:toggle_wishlist'),
            {'product_id': self.product.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)


# ─── Cart Logic Tests ─────────────────────────────────────────────────────────

class TestCartItemSubtotal(TestCase):

    def test_subtotal_regular_price(self):
        product = make_product(price='25.00')
        user = make_user(username='subtotaluser')
        cart = Cart.objects.create(user=user)
        item = CartItem.objects.create(cart=cart, product=product, quantity=4)
        self.assertEqual(item.get_subtotal(), Decimal('100.00'))

    def test_subtotal_uses_sale_price(self):
        product = make_product(price='100.00')
        product.sale_price = Decimal('60.00')
        product.save()
        user = make_user(username='saleuser')
        cart = Cart.objects.create(user=user)
        item = CartItem.objects.create(cart=cart, product=product, quantity=2)
        self.assertEqual(item.get_subtotal(), Decimal('120.00'))


# ─── Rating / Review Tests ────────────────────────────────────────────────────

class TestProductRating(TestCase):

    def setUp(self):
        self.product = make_product()
        self.user1 = make_user(username='ratinguser1')
        self.user2 = make_user(username='ratinguser2')

    def test_avg_rating_single_review(self):
        ProductRating.objects.create(product=self.product, user=self.user1, rating=4)
        self.assertEqual(self.product.get_avg_rating(), 4.0)

    def test_avg_rating_multiple_reviews(self):
        ProductRating.objects.create(product=self.product, user=self.user1, rating=4)
        ProductRating.objects.create(product=self.product, user=self.user2, rating=2)
        self.assertEqual(self.product.get_avg_rating(), 3.0)

    def test_rating_count(self):
        ProductRating.objects.create(product=self.product, user=self.user1, rating=5)
        self.assertEqual(self.product.get_rating_count(), 1)


# ─── AI Assistant View Tests ──────────────────────────────────────────────────

class TestAIAssistantView(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user(username='aiuser', password='ai123')

    def _mock_openrouter(self):
        import json as _json
        mock_resp = MagicMock()
        mock_resp.read.return_value = _json.dumps({
            'choices': [{'message': {'content': 'Hello! How can I help you today?'}}]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_ai_chat_requires_post(self):
        self.client.login(username='aiuser', password='ai123')
        response = self.client.get(reverse('shop:ai_assistant'))
        self.assertIn(response.status_code, [400, 405])

    @patch('urllib.request.urlopen')
    def test_ai_chat_post_returns_json(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_openrouter()
        self.client.login(username='aiuser', password='ai123')
        import json
        response = self.client.post(
            reverse('shop:ai_assistant'),
            json.dumps({'message': 'Hello'}),
            content_type='application/json',
        )
        self.assertIn(response.status_code, [200, 503])
        if response.status_code == 200:
            data = json.loads(response.content)
            self.assertIn('reply', data)

    @patch('urllib.request.urlopen')
    def test_ai_chat_anonymous_still_works(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_openrouter()
        import json
        response = self.client.post(
            reverse('shop:ai_assistant'),
            json.dumps({'message': 'Hello'}),
            content_type='application/json',
        )
        self.assertIn(response.status_code, [200, 503])


# ─── Policy / Static Page Tests ──────────────────────────────────────────────

class TestPolicyPages(TestCase):

    def test_shipping_policy_200(self):
        response = self.client.get(reverse('shop:shipping_policy'))
        self.assertEqual(response.status_code, 200)

    def test_returns_refunds_200(self):
        response = self.client.get(reverse('shop:returns_refunds'))
        self.assertEqual(response.status_code, 200)

    def test_contact_support_200(self):
        response = self.client.get(reverse('shop:contact_support'))
        self.assertEqual(response.status_code, 200)
