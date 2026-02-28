from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal

from index.models import Product, Category, Brand, SpecificationType, ProductSpecification, Review

User = get_user_model()


def make_category(name='Тест', slug='test'):
    cat, _ = Category.objects.get_or_create(name=name, slug=slug)
    return cat


def make_brand(name='BrandX', slug='brandx'):
    brand, _ = Brand.objects.get_or_create(name=name, slug=slug)
    return brand


def make_product(name='Товар', slug='tovar', price='1000.00', category=None, brand=None):
    return Product.objects.create(
        name=name, slug=slug,
        price=Decimal(price),
        category=category or make_category(),
        brand=brand or make_brand(),
    )


class CatalogViewTest(TestCase):
    def setUp(self):
        self.product = make_product('Ноутбук', 'noutbuk', '5000.00')

    def test_catalog_returns_200(self):
        response = self.client.get(reverse('index:index'))
        self.assertEqual(response.status_code, 200)

    def test_catalog_contains_product(self):
        response = self.client.get(reverse('index:index'))
        self.assertContains(response, 'Ноутбук')

    def test_catalog_filter_by_category(self):
        cat2 = make_category('Другая', 'other')
        other = make_product('Чужой', 'chujoj', category=cat2)
        response = self.client.get(reverse('index:index') + '?category=test')
        self.assertContains(response, 'Ноутбук')
        self.assertNotContains(response, 'Чужой')

    def test_catalog_filter_by_price(self):
        make_product('Дешёвый', 'deshovyj', '100.00')
        response = self.client.get(reverse('index:index') + '?price_from=500')
        self.assertContains(response, 'Ноутбук')
        self.assertNotContains(response, 'Дешёвый')

    def test_catalog_sort_price_asc(self):
        make_product('Дорогой', 'dorogoj', '9000.00')
        response = self.client.get(reverse('index:index') + '?sort=price_asc')
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        prices = [p.price for p in products]
        self.assertEqual(prices, sorted(prices))

    def test_catalog_sort_price_desc(self):
        make_product('Дорогой', 'dorogoj', '9000.00')
        response = self.client.get(reverse('index:index') + '?sort=price_desc')
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        prices = [p.price for p in products]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_pagination(self):
        for i in range(15):
            make_product(f'Product {i}', f'product-{i}', '999.00')
        response = self.client.get(reverse('index:index'))
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['products']), 12)


class ProductDetailViewTest(TestCase):
    def setUp(self):
        self.product = make_product('Ноутбук Lenovo', 'noutbuk-lenovo')

    def test_detail_returns_200(self):
        response = self.client.get(
            reverse('index:product_detail', kwargs={'slug': 'noutbuk-lenovo'})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_contains_product_name(self):
        response = self.client.get(
            reverse('index:product_detail', kwargs={'slug': 'noutbuk-lenovo'})
        )
        self.assertContains(response, 'Ноутбук Lenovo')

    def test_detail_404_for_unknown_slug(self):
        response = self.client.get(
            reverse('index:product_detail', kwargs={'slug': 'not-exists'})
        )
        self.assertEqual(response.status_code, 404)


class ReviewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.category = make_category()
        self.product = make_product('Телефон', 'phone', '20000.00', category=self.category)
        
        # Создаем характеристику для теста тегов
        self.spec_type = SpecificationType.objects.create(name='Экран')
        ProductSpecification.objects.create(product=self.product, spec_type=self.spec_type, value='OLED')

    def test_review_creation_and_tags(self):
        review = Review.objects.create(
            product=self.product,
            user=self.user,
            name='Test User',
            rating=5,
            comment='Особенно радует экран, а вот батарея не держит.'
        )
        # Проверяем, что тег "радует_экран" выделился (несмотря на "особенно")
        self.assertIn('радует_экран', review.tags)
        
    def test_negation_tags(self):
        # Создаем характеристику Батарея для теста
        spec_type_bat = SpecificationType.objects.create(name='Батарея')
        ProductSpecification.objects.create(product=self.product, spec_type=spec_type_bat, value='5000mAh')
        
        review = Review.objects.create(
            product=self.product,
            user=self.user,
            name='Test User',
            rating=2,
            comment='Не понравился экран, батарея слабая'
        )
        # Проверяем правильную обработку отрицания
        self.assertIn('не_понравился_экран', review.tags)
        self.assertIn('батарея_слабая', review.tags)

    def test_anonymous_cannot_post_review(self):
        response = self.client.post(
            reverse('index:product_detail', kwargs={'slug': self.product.slug}),
            {'rating': 5, 'comment': 'Anonymous review test'}
        )
        self.assertEqual(response.status_code, 302) # Redirect to login
        self.assertEqual(Review.objects.count(), 0)

    def test_authorized_can_post_review(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('index:product_detail', kwargs={'slug': self.product.slug}),
            {'rating': 4, 'comment': 'Valid review for testing purposes'}
        )
        self.assertEqual(response.status_code, 302) # Success redirect
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.first().user, self.user)

class SearchViewTest(TestCase):
    def setUp(self):
        self.product = make_product('Ноутбук Lenovo X1', 'lenovo-x1')

    def test_search_finds_product(self):
        response = self.client.get(reverse('index:search') + '?q=Lenovo')
        self.assertContains(response, 'Ноутбук Lenovo X1')

    def test_search_empty_query_returns_no_products(self):
        response = self.client.get(reverse('index:search') + '?q=')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['products']), 0)
