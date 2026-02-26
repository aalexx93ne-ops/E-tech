from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from index.models import Product, Category, Brand, Stock
from orders.models import Order, OrderItem

User = get_user_model()


def make_product(name='Товар', price='1000.00', stock_qty=10):
    category, _ = Category.objects.get_or_create(name='Тест', slug='test')
    brand, _ = Brand.objects.get_or_create(name='BrandX', slug='brandx')
    product = Product.objects.create(
        name=name,
        slug=name.lower().replace(' ', '-'),
        price=Decimal(price),
        category=category,
        brand=brand,
    )
    Stock.objects.create(product=product, quantity=stock_qty)
    return product


def make_order(user=None):
    return Order.objects.create(
        first_name='Иван',
        last_name='Иванов',
        email='ivan@example.com',
        address='ул. Ленина, 1',
        city='Москва',
        user=user,
    )


class OrderModelTest(TestCase):
    """Тесты модели Order."""

    def test_order_creation(self):
        order = make_order()
        self.assertEqual(order.status, Order.STATUS_NEW)
        self.assertFalse(order.paid)

    def test_get_total_cost(self):
        product = make_product('Ноутбук', '50000.00')
        order = make_order()
        OrderItem.objects.create(order=order, product=product, price=Decimal('50000.00'), quantity=2)
        self.assertEqual(order.get_total_cost(), Decimal('100000.00'))

    def test_order_str(self):
        order = make_order()
        self.assertEqual(str(order), f'Заказ {order.id}')

    def test_order_with_user(self):
        user = User.objects.create_user(username='testuser', email='u@test.com', password='pass')
        order = make_order(user=user)
        self.assertEqual(order.user, user)

    def test_order_without_user(self):
        order = make_order()
        self.assertIsNone(order.user)


class OrderItemTest(TestCase):
    """Тесты модели OrderItem."""

    def setUp(self):
        self.product = make_product()
        self.order = make_order()

    def test_get_cost(self):
        item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            price=Decimal('1000.00'),
            quantity=3,
        )
        self.assertEqual(item.get_cost(), Decimal('3000.00'))


class OrderCreateViewTest(TestCase):
    """Тесты view оформления заказа."""

    def setUp(self):
        self.product = make_product('Телефон', '30000.00', stock_qty=5)

    def _add_to_cart(self, qty=1):
        self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': str(qty), 'update': 'false'},
        )

    def test_empty_cart_redirects(self):
        response = self.client.get('/orders/create/')
        self.assertRedirects(response, '/cart/')

    def test_order_form_renders(self):
        self._add_to_cart()
        response = self.client.get('/orders/create/')
        self.assertEqual(response.status_code, 200)

    def test_order_create_post(self):
        self._add_to_cart(qty=2)
        response = self.client.post('/orders/create/', {
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'email': 'ivan@example.com',
            'address': 'ул. Ленина, 1',
            'city': 'Москва',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.exists())
        order = Order.objects.first()
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().quantity, 2)

    def test_stock_decreases_after_order(self):
        """Stock должен уменьшиться после оформления заказа."""
        self._add_to_cart(qty=3)
        self.client.post('/orders/create/', {
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'email': 'ivan@example.com',
            'address': 'ул. Ленина, 1',
            'city': 'Москва',
        })
        self.product.stock.refresh_from_db()
        self.assertEqual(self.product.stock.quantity, 2)  # 5 - 3

    def test_cart_cleared_after_order(self):
        self._add_to_cart(qty=1)
        self.client.post('/orders/create/', {
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'email': 'ivan@example.com',
            'address': 'ул. Ленина, 1',
            'city': 'Москва',
        })
        # После заказа корзина пуста — повторный GET на create редиректит
        response = self.client.get('/orders/create/')
        self.assertRedirects(response, '/cart/')


class OrderCancelStockTest(TestCase):
    """Возврат остатков при отмене заказа."""

    def setUp(self):
        self.product = make_product('Камера', '15000.00', stock_qty=10)
        self.order = make_order()
        OrderItem.objects.create(
            order=self.order, product=self.product,
            price=self.product.price, quantity=4,
        )
        # Имитируем списание при создании заказа
        Stock.objects.filter(product=self.product).update(quantity=6)  # 10 - 4

    def test_stock_restored_on_cancel(self):
        self.order.status = Order.STATUS_CANCELLED
        self.order.save()
        self.product.stock.refresh_from_db()
        self.assertEqual(self.product.stock.quantity, 10)  # 6 + 4

    def test_stock_not_restored_twice(self):
        self.order.status = Order.STATUS_CANCELLED
        self.order.save()
        # Второй save с тем же статусом — остатки не должны удвоиться
        self.order.save()
        self.product.stock.refresh_from_db()
        self.assertEqual(self.product.stock.quantity, 10)
