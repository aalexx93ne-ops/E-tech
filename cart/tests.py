from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import get_user_model
from unittest.mock import MagicMock

from index.models import Product, Category, Brand
from cart.cart import Cart
from cart.models import DBCart, DBCartItem

User = get_user_model()


def make_request(user=None):
    factory = RequestFactory()
    request = factory.get('/')
    request.session = SessionStore()
    request.session.create()
    request.user = user or MagicMock(is_authenticated=False)
    return request


def make_product(name='Тестовый товар', price='1000.00'):
    category, _ = Category.objects.get_or_create(name='Тест', slug='test')
    brand, _ = Brand.objects.get_or_create(name='BrandX', slug='brandx')
    return Product.objects.create(
        name=name,
        slug=name.lower().replace(' ', '-'),
        price=Decimal(price),
        category=category,
        brand=brand,
    )


class SessionCartTest(TestCase):
    """Тесты сессионной корзины (анонимный пользователь)."""

    def setUp(self):
        self.request = make_request()
        self.product = make_product()

    def test_add_product(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=2)
        self.assertEqual(len(cart), 2)

    def test_add_product_increments(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=1)
        cart.add(self.product, quantity=3)
        self.assertEqual(len(cart), 4)

    def test_add_product_update_quantity(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=5)
        cart.add(self.product, quantity=2, update_quantity=True)
        self.assertEqual(len(cart), 2)

    def test_remove_product(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=1)
        cart.remove(self.product)
        self.assertEqual(len(cart), 0)

    def test_clear_cart(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=3)
        cart.clear()
        self.assertEqual(len(cart), 0)

    def test_total_price(self):
        product2 = make_product('Товар 2', '500.00')
        cart = Cart(self.request)
        cart.add(self.product, quantity=2)
        cart.add(product2, quantity=1)
        self.assertEqual(cart.get_total_price(), Decimal('2500.00'))

    def test_iter_returns_items(self):
        cart = Cart(self.request)
        cart.add(self.product, quantity=2)
        items = list(cart)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['quantity'], 2)
        self.assertEqual(items[0]['product'], self.product)


class DBCartTest(TestCase):
    """Тесты БД-корзины (авторизованный пользователь)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@test.com', password='pass123'
        )
        self.product = make_product()

    def make_auth_request(self):
        return make_request(user=self.user)

    def test_add_product_to_db_cart(self):
        cart = Cart(self.make_auth_request())
        cart.add(self.product, quantity=2)
        self.assertTrue(DBCart.objects.filter(user=self.user).exists())
        item = DBCartItem.objects.get(cart__user=self.user, product=self.product)
        self.assertEqual(item.quantity, 2)

    def test_remove_product_from_db_cart(self):
        cart = Cart(self.make_auth_request())
        cart.add(self.product, quantity=1)
        cart.remove(self.product)
        self.assertFalse(
            DBCartItem.objects.filter(cart__user=self.user, product=self.product).exists()
        )

    def test_clear_db_cart(self):
        cart = Cart(self.make_auth_request())
        cart.add(self.product, quantity=3)
        cart.clear()
        self.assertEqual(
            DBCartItem.objects.filter(cart__user=self.user).count(), 0
        )

    def test_len_db_cart(self):
        cart = Cart(self.make_auth_request())
        cart.add(self.product, quantity=4)
        self.assertEqual(len(cart), 4)


class CartViewTest(TestCase):
    """Тесты view корзины."""

    def setUp(self):
        self.product = make_product()

    def test_cart_add_view(self):
        response = self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': '2', 'update': 'false'},
        )
        self.assertIn(response.status_code, [200, 302])

    def test_cart_add_invalid_quantity_no_crash(self):
        """Некорректный quantity не должен давать 500."""
        response = self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': 'abc', 'update': 'false'},
        )
        self.assertNotEqual(response.status_code, 500)

    def test_cart_remove_view(self):
        self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': '1', 'update': 'false'},
        )
        response = self.client.post(f'/cart/remove/{self.product.id}/')
        self.assertIn(response.status_code, [200, 302])
