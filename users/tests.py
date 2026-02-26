from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal

from orders.models import Order
from index.models import Product, Category, Brand, Stock

User = get_user_model()


def make_user(username='user1', email='user1@test.com', password='pass123'):
    return User.objects.create_user(username=username, email=email, password=password)


def make_product():
    cat, _ = Category.objects.get_or_create(name='Тест', slug='test')
    brand, _ = Brand.objects.get_or_create(name='BrandX', slug='brandx')
    p = Product.objects.create(
        name='Товар', slug='tovar', price=Decimal('1000.00'),
        category=cat, brand=brand,
    )
    Stock.objects.create(product=p, quantity=10)
    return p


class ProfileViewTest(TestCase):
    def setUp(self):
        self.user = make_user()
        # USERNAME_FIELD = email, поэтому передаём email в поле username
        self.client.force_login(self.user)

    def test_profile_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_returns_200(self):
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_shows_orders(self):
        order = Order.objects.create(
            user=self.user, first_name='Иван', last_name='Иванов',
            email='test@test.com', address='ул. Ленина', city='Москва',
        )
        response = self.client.get(reverse('users:profile'))
        self.assertContains(response, f'#{order.id}')

    def test_profile_pagination(self):
        for i in range(15):
            Order.objects.create(
                user=self.user, first_name='Иван', last_name='Иванов',
                email='test@test.com', address='ул. Ленина', city='Москва',
            )
        response = self.client.get(reverse('users:profile'))
        orders = response.context['orders']
        self.assertTrue(orders.has_other_pages())
        self.assertEqual(len(orders), 10)

    def test_profile_pagination_page2(self):
        for i in range(15):
            Order.objects.create(
                user=self.user, first_name='Иван', last_name='Иванов',
                email='test@test.com', address='ул. Ленина', city='Москва',
            )
        response = self.client.get(reverse('users:profile') + '?page=2')
        orders = response.context['orders']
        self.assertEqual(orders.number, 2)
        self.assertEqual(len(orders), 5)


class ProfileEditViewTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_edit_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('users:profile_edit'))
        self.assertEqual(response.status_code, 302)

    def test_edit_returns_200(self):
        response = self.client.get(reverse('users:profile_edit'))
        self.assertEqual(response.status_code, 200)

    def test_edit_saves_city(self):
        self.client.post(reverse('users:profile_edit'), {
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'email': self.user.email,
            'city': 'Санкт-Петербург',
            'address': '',
            'postal_code': '',
            'phone': '',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.city, 'Санкт-Петербург')


class OrderDetailViewTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user('user2', 'user2@test.com')
        self.client.force_login(self.user)
        self.order = Order.objects.create(
            user=self.user, first_name='Иван', last_name='Иванов',
            email='test@test.com', address='ул. Ленина', city='Москва',
        )

    def test_order_detail_returns_200(self):
        response = self.client.get(
            reverse('users:order_detail', kwargs={'order_id': self.order.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_order_detail_forbidden_for_other_user(self):
        self.client.force_login(self.other)
        response = self.client.get(
            reverse('users:order_detail', kwargs={'order_id': self.order.id})
        )
        self.assertEqual(response.status_code, 404)
