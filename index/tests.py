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


# === Тесты для системы сравнения товаров ===

class ComparisonServiceTest(TestCase):
    """Тесты для сервиса сравнения товаров."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.category = make_category('Смартфоны', 'smartfony')
        self.brand = make_brand('BrandX', 'brandx')
        
        # Создаём 2 товара
        self.product1 = make_product(
            name='iPhone 15',
            slug='iphone-15',
            price='80000.00',
            category=self.category,
            brand=self.brand
        )
        self.product2 = make_product(
            name='Samsung S24',
            slug='samsung-s24',
            price='90000.00',
            category=self.category,
            brand=self.brand
        )
        
        # Создаём типы характеристик с настройками сравнения
        self.ram_spec_type = SpecificationType.objects.create(
            name='Оперативная память',
            comparison_type='higher_better',
            unit='ГБ',
            priority=10,
            is_comparable=True
        )
        
        self.storage_spec_type = SpecificationType.objects.create(
            name='Накопитель',
            comparison_type='higher_better',
            unit='ГБ',
            priority=9,
            is_comparable=True
        )
        
        self.panel_spec_type = SpecificationType.objects.create(
            name='Тип экрана',
            comparison_type='categorical',
            unit='',
            priority=15,
            is_comparable=True,
            category_map={'AMOLED': 100, 'OLED': 95, 'IPS': 70, 'TN': 40}
        )
        
        # Создаём характеристики для товаров
        ProductSpecification.objects.create(
            product=self.product1,
            spec_type=self.ram_spec_type,
            value='8 ГБ'
        )
        ProductSpecification.objects.create(
            product=self.product2,
            spec_type=self.ram_spec_type,
            value='12 ГБ'
        )
        
        ProductSpecification.objects.create(
            product=self.product1,
            spec_type=self.storage_spec_type,
            value='256 ГБ'
        )
        ProductSpecification.objects.create(
            product=self.product2,
            spec_type=self.storage_spec_type,
            value='128 ГБ'
        )
        
        ProductSpecification.objects.create(
            product=self.product1,
            spec_type=self.panel_spec_type,
            value='OLED'
        )
        ProductSpecification.objects.create(
            product=self.product2,
            spec_type=self.panel_spec_type,
            value='IPS'
        )

    def test_validate_products_correct_count(self):
        """Проверка валидации: ровно 2 товара."""
        from index.services import ComparisonService
        
        # Слишком мало товаров
        success, error, products = ComparisonService.validate_products([self.product1.id])
        self.assertFalse(success)
        self.assertIn('ровно 2', error)
        
        # Слишком много товаров
        product3 = make_product('Third', 'third')
        success, error, products = ComparisonService.validate_products([
            self.product1.id, self.product2.id, product3.id
        ])
        self.assertFalse(success)

    def test_validate_products_same_category(self):
        """Проверка валидации: одна категория."""
        from index.services import ComparisonService
        
        other_category = make_category('Другая', 'other')
        other_product = make_product('Other', 'other', category=other_category)
        
        success, error, products = ComparisonService.validate_products([
            self.product1.id, other_product.id
        ])
        self.assertFalse(success)
        self.assertIn('одной категории', error)

    def test_get_comparison_data(self):
        """Проверка получения данных сравнения."""
        from index.services import ComparisonService
        
        data = ComparisonService.get_comparison_data([self.product1.id, self.product2.id])
        
        self.assertNotIn('error', data)
        self.assertEqual(data['category']['slug'], 'smartfony')
        self.assertEqual(len(data['products']), 2)
        self.assertGreater(len(data['metrics']), 0)
        
        # Проверка метрики RAM (higher_better) - ищем по названию типа характеристики
        ram_metric = None
        storage_metric = None
        
        for m in data['metrics']:
            if 'оперативная' in m['name'].lower() or 'озу' in m['name'].lower():
                ram_metric = m
            elif 'накопитель' in m['name'].lower() or 'встроенная' in m['name'].lower():
                storage_metric = m
        
        # Проверяем RAM
        if ram_metric:
            product1_data = next(p for p in ram_metric['products'] if p['product_id'] == self.product1.id)
            product2_data = next(p for p in ram_metric['products'] if p['product_id'] == self.product2.id)
            
            self.assertFalse(product1_data['is_best'])
            self.assertTrue(product1_data['is_worst'])
            self.assertTrue(product2_data['is_best'])
            self.assertFalse(product2_data['is_worst'])
        
        # Проверяем накопитель
        if storage_metric:
            product1_storage = next(p for p in storage_metric['products'] if p['product_id'] == self.product1.id)
            product2_storage = next(p for p in storage_metric['products'] if p['product_id'] == self.product2.id)
            
            self.assertTrue(product1_storage['is_best'])  # 256 ГБ > 128 ГБ
            self.assertFalse(product2_storage['is_best'])

    def test_parse_value_numeric(self):
        """Проверка парсинга числовых значений."""
        from index.services import ComparisonService
        
        # Целое число
        result = ComparisonService.parse_value('8 ГБ', 'higher_better')
        self.assertEqual(result, Decimal('8'))
        
        # Дробное число
        result = ComparisonService.parse_value('6.7 дюймов', 'higher_better')
        self.assertEqual(result, Decimal('6.7'))
        
        # С запятой
        result = ComparisonService.parse_value('150,5 г', 'lower_better')
        self.assertEqual(result, Decimal('150.5'))

    def test_parse_value_categorical(self):
        """Проверка парсинга категориальных значений."""
        from index.services import ComparisonService
        
        result = ComparisonService.parse_value('AMOLED', 'categorical')
        self.assertEqual(result, 'AMOLED')
        
        result = ComparisonService.parse_value('IPS', 'categorical')
        self.assertEqual(result, 'IPS')

    def test_parse_value_boolean(self):
        """Проверка парсинга булевых значений."""
        from index.services import ComparisonService
        
        self.assertTrue(ComparisonService.parse_value('Да', 'boolean'))
        self.assertTrue(ComparisonService.parse_value('yes', 'boolean'))
        self.assertTrue(ComparisonService.parse_value('Есть', 'boolean'))
        self.assertFalse(ComparisonService.parse_value('Нет', 'boolean'))


class ComparisonViewTest(TestCase):
    """Тесты для view сравнения товаров."""
    
    def setUp(self):
        self.category = make_category('Смартфоны', 'smartfony')
        self.product1 = make_product('iPhone', 'iphone', category=self.category)
        self.product2 = make_product('Samsung', 'samsung', category=self.category)
        
        self.spec_type = SpecificationType.objects.create(
            name='ОЗУ',
            comparison_type='higher_better',
            unit='ГБ',
            is_comparable=True
        )

    def test_comparison_view_no_products(self):
        """Тест: нет товаров."""
        response = self.client.get(reverse('index:comparison'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Выберите товары')

    def test_comparison_view_invalid_ids(self):
        """Тест: некорректные ID."""
        response = self.client.get(reverse('index:comparison') + '?product_ids=abc')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Некорректный формат')

    def test_comparison_view_wrong_count(self):
        """Тест: не 2 товара."""
        response = self.client.get(reverse('index:comparison') + '?product_ids=1')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ровно 2')

    def test_comparison_view_success(self):
        """Тест: успешное сравнение."""
        slug = reverse('index:comparison') + f'?product_ids={self.product1.id},{self.product2.id}'
        response = self.client.get(slug)
        self.assertEqual(response.status_code, 200)


class ComparisonAPITest(TestCase):
    """Тесты для API сравнения."""
    
    def setUp(self):
        self.category = make_category('Смартфоны', 'smartfony')
        self.product1 = make_product('iPhone', 'iphone', category=self.category)
        self.product2 = make_product('Samsung', 'samsung', category=self.category)

    def test_api_no_product_ids(self):
        """Тест: нет ID товаров."""
        response = self.client.get(reverse('index:api_comparison'))
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {'error': 'Не указаны ID товаров'})

    def test_api_invalid_format(self):
        """Тест: некорректный формат ID."""
        response = self.client.get(reverse('index:api_comparison') + '?product_ids=abc')
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {'error': 'Некорректный формат ID товаров'})

    def test_api_success(self):
        """Тест: успешный запрос."""
        url = reverse('index:api_comparison') + f'?product_ids={self.product1.id},{self.product2.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('category', data)
        self.assertIn('products', data)
        self.assertIn('metrics', data)
