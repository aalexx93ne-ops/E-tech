"""
Сервис сравнения товаров.
Логика сравнения характеристик товаров в рамках одной категории.
"""
import re
from decimal import Decimal
from django.db.models import Prefetch
from django.core.cache import cache
from index.models import Product, SpecificationType, ProductSpecification


class ComparisonService:
    """Сервис для сравнения товаров."""
    
    CACHE_TIMEOUT = 300  # 5 минут

    @staticmethod
    def validate_products(product_ids):
        """
        Проверяет, что можно сравнивать товары.
        
        Args:
            product_ids: Список ID товаров
            
        Returns:
            tuple: (success: bool, error: str|None, products: QuerySet|None)
        """
        if len(product_ids) != 2:
            return False, "Для сравнения нужно выбрать ровно 2 товара", None
        
        products = Product.objects.filter(id__in=product_ids).select_related(
            'category', 'brand'
        )
        
        if products.count() != 2:
            return False, "Один или оба товара не найдены", None
        
        # Проверяем, что товары из одной категории
        categories = set(p.category_id for p in products)
        if len(categories) > 1:
            return False, "Товары должны быть из одной категории", None
        
        return True, None, products

    @staticmethod
    def parse_value(raw_value, comparison_type):
        """
        Извлекает значение из текстового поля в зависимости от типа сравнения.
        
        Args:
            raw_value: Текстовое значение (например, "8 ГБ", "AMOLED")
            comparison_type: Тип сравнения
            
        Returns:
            Decimal|str|bool|None: Распарсенное значение
        """
        if not raw_value:
            return None
        
        if comparison_type == 'categorical':
            return raw_value.strip()
        
        if comparison_type == 'boolean':
            raw_lower = raw_value.lower()
            return any(x in raw_lower for x in ['да', 'yes', 'есть', '1', 'true', '+'])
        
        # Числовые типы: извлекаем число
        # Примеры: "8 ГБ", "256GB", "150г", "6.7 дюймов"
        raw_clean = raw_value.replace(',', '.').strip()
        
        # Извлекаем первое число (целое или дробное)
        match = re.search(r'([\d.]+)', raw_clean)
        if match:
            try:
                return Decimal(match.group(1))
            except (ValueError, ArithmeticError):
                pass
        
        return None

    @staticmethod
    def get_comparison_data(product_ids):
        """
        Получает данные для сравнения товаров.
        Использует кэширование для производительности.
        
        Args:
            product_ids: Список ID товаров (ровно 2)
            
        Returns:
            dict: Данные для сравнения или error
        """
        # Проверяем кэш
        cache_key = f'comparison:{":".join(map(str, sorted(product_ids)))}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # Валидация
        success, error, products = ComparisonService.validate_products(product_ids)
        if not success:
            return {'error': error}
        
        category = products[0].category
        
        # Получаем активные типы характеристик для сравнения
        spec_types = SpecificationType.objects.filter(
            is_comparable=True
        ).order_by('-priority', 'name')
        
        # Получаем характеристики для всех товаров с prefetch
        specs = ProductSpecification.objects.filter(
            product__in=products,
            spec_type__in=spec_types
        ).select_related('spec_type', 'product')
        
        # Группируем характеристики по товарам
        product_specs = {}
        for spec in specs:
            if spec.product_id not in product_specs:
                product_specs[spec.product_id] = {}
            product_specs[spec.product_id][spec.spec_type_id] = spec
        
        # Формируем результат
        result_spec_types = []
        for spec_type in spec_types:
            spec_type_data = {
                'id': spec_type.id,
                'name': spec_type.name,
                'comparison_type': spec_type.comparison_type,
                'unit': spec_type.unit,
                'priority': spec_type.priority,
                'category_map': spec_type.category_map,
                'products': []
            }
            
            # Получаем значения для каждого товара
            values = []
            for product in products:
                spec = product_specs.get(product.id, {}).get(spec_type.id)
                
                if spec:
                    raw_value = spec.value
                    normalized = ComparisonService.parse_value(
                        raw_value, 
                        spec_type.comparison_type
                    )
                else:
                    raw_value = '—'
                    normalized = None
                
                values.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'product_image': product.main_image.url if product.main_image else None,
                    'raw_value': raw_value,
                    'normalized_value': normalized,
                })
            
            # Определяем победителя
            values = ComparisonService._determine_winner(values, spec_type)
            spec_type_data['products'] = values
            
            result_spec_types.append(spec_type_data)
        
        result = {
            'category': {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
            },
            'products': [
                {
                    'id': p.id,
                    'name': p.name,
                    'slug': p.slug,
                    'image': p.main_image.url if p.main_image else None,
                    'price': str(p.price),
                    'final_price': str(p.get_final_price()),
                }
                for p in products
            ],
            'metrics': result_spec_types,
        }
        
        # Сохраняем в кэш
        cache.set(cache_key, result, ComparisonService.CACHE_TIMEOUT)
        
        return result

    @staticmethod
    def _determine_winner(values, spec_type):
        """
        Определяет победителя по характеристике.
        
        Args:
            values: Список значений для товаров
            spec_type: SpecificationType с настройками сравнения
            
        Returns:
            list: Values с добавленными is_best, is_worst, is_tie
        """
        if len(values) != 2:
            return values
        
        val_a = values[0]['normalized_value']
        val_b = values[1]['normalized_value']
        
        # Если нет значений — ничья
        if val_a is None and val_b is None:
            for v in values:
                v['is_best'] = False
                v['is_worst'] = False
                v['is_tie'] = True
            return values
        
        # Если одно значение отсутствует
        if val_a is None:
            values[1]['is_best'] = True
            values[1]['is_worst'] = False
            values[1]['is_tie'] = False
            values[0]['is_best'] = False
            values[0]['is_worst'] = True
            values[0]['is_tie'] = False
            return values
        
        if val_b is None:
            values[0]['is_best'] = True
            values[0]['is_worst'] = False
            values[0]['is_tie'] = False
            values[1]['is_best'] = False
            values[1]['is_worst'] = True
            values[1]['is_tie'] = False
            return values
        
        # Сравниваем значения
        if val_a == val_b:
            # Ничья
            for v in values:
                v['is_best'] = False
                v['is_worst'] = False
                v['is_tie'] = True
        else:
            # Определяем победителя по типу сравнения
            if spec_type.comparison_type == 'higher_better':
                winner_idx = 0 if val_a > val_b else 1
            elif spec_type.comparison_type == 'lower_better':
                winner_idx = 0 if val_a < val_b else 1
            elif spec_type.comparison_type == 'categorical':
                # Используем category_map для сравнения
                score_a = spec_type.category_map.get(str(val_a), 0)
                score_b = spec_type.category_map.get(str(val_b), 0)
                winner_idx = 0 if score_a > score_b else (1 if score_b > score_a else -1)
            elif spec_type.comparison_type == 'boolean':
                winner_idx = 0 if val_a and not val_b else (1 if val_b and not val_a else -1)
            else:
                winner_idx = 0 if val_a > val_b else 1
            
            if winner_idx == -1:
                # Ничья в categorical/boolean
                for v in values:
                    v['is_best'] = False
                    v['is_worst'] = False
                    v['is_tie'] = True
            else:
                values[winner_idx]['is_best'] = True
                values[winner_idx]['is_worst'] = False
                values[winner_idx]['is_tie'] = False
                
                loser_idx = 1 - winner_idx
                values[loser_idx]['is_best'] = False
                values[loser_idx]['is_worst'] = True
                values[loser_idx]['is_tie'] = False
        
        return values

    @staticmethod
    def invalidate_cache(product_ids):
        """
        Очищает кэш для указанных товаров.
        Вызывать после обновления характеристик.
        """
        cache_key = f'comparison:{":".join(map(str, sorted(product_ids)))}'
        cache.delete(cache_key)
