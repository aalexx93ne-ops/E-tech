#!/usr/bin/env python
"""
Генератор синтетических данных для товаров.
Создает 48 карточек товаров (ноутбуки и телефоны).
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'appx.settings')
django.setup()

from index.models import Product, Category, Brand, Tag
from decimal import Decimal
import random

# Данные для ноутбуков
LAPTOP_BRANDS = ['Apple', 'Dell', 'HP', 'Lenovo', 'Asus', 'Acer', 'MSI', 'Razer', 'Huawei', 'Xiaomi']
LAPTOP_MODELS = [
    'ProBook 450', 'EliteBook 840', 'Pavilion 15', 'Envy 13', 'Spectre x360',
    'ThinkPad X1', 'ThinkPad T14', 'IdeaPad 5', 'Yoga 7i', 'Legion 5 Pro',
    'VivoBook 15', 'ZenBook 14', 'ROG Strix G15', 'TUF Gaming F15', 'ExpertBook',
    'Aspire 5', 'Swift 3', 'Nitro 5', 'Predator Helios', 'ConceptD',
    'MacBook Air M1', 'MacBook Air M2', 'MacBook Pro 14', 'MacBook Pro 16',
    'MateBook D15', 'MateBook X Pro', 'RedmiBook 15', 'Mi Notebook Pro',
    'Blade 15', 'Blade Stealth 13', 'XPS 13', 'XPS 15', 'Inspiron 15',
    'Latitude 5420', 'Precision 3560', 'Katana GF66', 'Pulse GL66', 'Summit E14',
    'Modern 15', 'Prestige 14', 'Creator Z16', 'Sword 15', 'Alpha 15',
    'Nitro V15', 'Aspire Vero', 'Enduro Urban', 'TravelMate P2'
]

LAPTOP_SPECS = [
    'Intel Core i5-1235U, 8GB RAM, 256GB SSD, 15.6" FHD',
    'Intel Core i7-1255U, 16GB RAM, 512GB SSD, 15.6" FHD IPS',
    'AMD Ryzen 5 5625U, 8GB RAM, 512GB SSD, 14" FHD',
    'AMD Ryzen 7 5825U, 16GB RAM, 1TB SSD, 15.6" FHD',
    'Intel Core i5-1135G7, 8GB RAM, 256GB SSD, 13.3" FHD',
    'Intel Core i7-1165G7, 16GB RAM, 512GB SSD, 14" 2K',
    'Apple M1, 8GB RAM, 256GB SSD, 13.3" Retina',
    'Apple M2, 16GB RAM, 512GB SSD, 13.6" Retina',
    'Intel Core i9-12900H, 32GB RAM, 1TB SSD, RTX 3060, 15.6" 165Hz',
    'AMD Ryzen 9 5900HX, 16GB RAM, 1TB SSD, RTX 3070, 17.3" 144Hz',
    'Intel Core i5-1240P, 16GB RAM, 512GB SSD, 14" OLED',
    'Intel Core i7-12700H, 32GB RAM, 1TB SSD, RTX 3080 Ti, 16" 240Hz',
]

# Данные для телефонов
PHONE_BRANDS = ['Apple', 'Samsung', 'Xiaomi', 'OnePlus', 'Google', 'Huawei', 'OPPO', 'Vivo', 'Realme', 'Nothing']
PHONE_MODELS = [
    'iPhone 14', 'iPhone 14 Pro', 'iPhone 14 Pro Max', 'iPhone 13', 'iPhone SE 2022',
    'Galaxy S23', 'Galaxy S23+', 'Galaxy S23 Ultra', 'Galaxy A54', 'Galaxy A34',
    'Redmi Note 12', 'Redmi Note 12 Pro', 'Mi 13', 'Mi 13 Pro', 'POCO F5',
    'OnePlus 11', 'OnePlus Nord 3', 'OnePlus 10T', 'Pixel 7', 'Pixel 7 Pro',
    'Pixel 6a', 'Mate 50 Pro', 'P60 Pro', 'nova 11', 'Find X6 Pro',
    'Reno 10 Pro', 'X90 Pro', 'V27 Pro', 'GT Neo 5', '11 Pro',
    'Galaxy Z Flip 5', 'Galaxy Z Fold 5', 'iPhone 15', 'iPhone 15 Pro',
    'Redmi 12', 'Mi 13 Lite', 'OnePlus 11R', 'Pixel 7a', 'Mate X3',
    'Find N2 Flip', 'Reno 8T', 'X80 Lite', 'V25', 'GT 3',
    'Galaxy S22', 'iPhone 12', 'Mi 12T', 'OnePlus 10 Pro'
]

PHONE_SPECS = [
    '6.1" OLED, 128GB, 5G, 3279 mAh',
    '6.7" OLED, 256GB, 5G, 4323 mAh',
    '6.1" OLED 120Hz, 128GB, 5G, A16 Bionic',
    '6.7" OLED 120Hz, 256GB, 5G, A16 Bionic, 48MP',
    '6.1" OLED, 64GB, 5G, A15 Bionic',
    '6.1" AMOLED 120Hz, 128GB, 5G, Snapdragon 8 Gen 2',
    '6.6" AMOLED 120Hz, 256GB, 5G, Snapdragon 8 Gen 2',
    '6.8" AMOLED 120Hz, 256GB, 5G, Snapdragon 8 Gen 2, 200MP',
    '6.4" AMOLED 120Hz, 128GB, 5G, Exynos 1380, 5000 mAh',
    '6.6" AMOLED 120Hz, 128GB, 5G, Dimensity 1080, 5000 mAh',
    '6.67" AMOLED 120Hz, 128GB, 5G, Snapdragon 4 Gen 1, 5000 mAh',
    '6.67" AMOLED 120Hz, 256GB, 5G, Dimensity 1080, 67W',
    '6.36" AMOLED 120Hz, 128GB, 5G, Snapdragon 8 Gen 2',
    '6.73" AMOLED 120Hz, 256GB, 5G, Snapdragon 8 Gen 2, Leica',
    '6.67" AMOLED 120Hz, 256GB, 5G, Snapdragon 7+ Gen 2, 67W',
    '6.7" AMOLED 120Hz, 128GB, 5G, Snapdragon 8 Gen 2, 100W',
    '6.74" AMOLED 120Hz, 256GB, 5G, Dimensity 9000, 80W',
    '6.7" AMOLED 120Hz, 256GB, 5G, Snapdragon 8+ Gen 1, 150W',
    '6.3" OLED 90Hz, 128GB, 5G, Tensor G2',
    '6.7" OLED 120Hz, 128GB, 5G, Tensor G2, 48MP',
]


def create_laptops(category, count=24):
    """Создает ноутбуки."""
    products = []
    used_names = set()
    
    for i in range(count):
        brand_name = random.choice(LAPTOP_BRANDS)
        model = random.choice(LAPTOP_MODELS)
        name = f"{brand_name} {model}"
        
        # Уникальность имени
        counter = 1
        original_name = name
        while name in used_names:
            name = f"{original_name} ({counter})"
            counter += 1
        used_names.add(name)
        
        # Получаем или создаем бренд
        brand, _ = Brand.objects.get_or_create(name=brand_name)
        
        # Цена в зависимости от бренда и характеристик
        base_price = random.choice([
            Decimal('45000.00'), Decimal('55000.00'), Decimal('65000.00'),
            Decimal('75000.00'), Decimal('85000.00'), Decimal('95000.00'),
            Decimal('110000.00'), Decimal('130000.00'), Decimal('150000.00'),
            Decimal('180000.00'), Decimal('220000.00'), Decimal('280000.00')
        ])
        
        # Apple и игровые ноутбуки дороже
        if brand_name in ['Apple', 'Razer']:
            base_price *= Decimal('1.3')
        elif 'Gaming' in model or 'ROG' in model or 'Legion' in model:
            base_price *= Decimal('1.2')
        
        description = f"Ноутбук {name}. {random.choice(LAPTOP_SPECS)}. Идеально подходит для работы и развлечений."
        
        product = Product(
            name=name,
            description=description,
            price=base_price,
            category=category,
            brand=brand
        )
        products.append(product)
    
    return products


def create_phones(category, count=24):
    """Создает телефоны."""
    products = []
    used_names = set()
    
    for i in range(count):
        brand_name = random.choice(PHONE_BRANDS)
        model = random.choice(PHONE_MODELS)
        name = f"{brand_name} {model}"
        
        # Уникальность имени
        counter = 1
        original_name = name
        while name in used_names:
            name = f"{original_name} ({counter})"
            counter += 1
        used_names.add(name)
        
        # Получаем или создаем бренд
        brand, _ = Brand.objects.get_or_create(name=brand_name)
        
        # Цена в зависимости от бренда и модели
        base_price = random.choice([
            Decimal('15000.00'), Decimal('20000.00'), Decimal('25000.00'),
            Decimal('35000.00'), Decimal('45000.00'), Decimal('55000.00'),
            Decimal('65000.00'), Decimal('75000.00'), Decimal('85000.00'),
            Decimal('95000.00'), Decimal('110000.00'), Decimal('130000.00')
        ])
        
        # Флагманские модели дороже
        if 'Pro' in model or 'Ultra' in model or 'Max' in model:
            base_price *= Decimal('1.4')
        elif 'Fold' in model or 'Flip' in model:
            base_price *= Decimal('1.5')
        
        description = f"Смартфон {name}. {random.choice(PHONE_SPECS)}. Отличная производительность и камера."
        
        product = Product(
            name=name,
            description=description,
            price=base_price,
            category=category,
            brand=brand
        )
        products.append(product)
    
    return products


def main():
    print("Начинаем генерацию синтетических данных...")
    
    # Создаем категории
    laptops_category, _ = Category.objects.get_or_create(
        name='Ноутбуки',
        defaults={'slug': 'laptops'}
    )
    phones_category, _ = Category.objects.get_or_create(
        name='Смартфоны',
        defaults={'slug': 'smartphones'}
    )
    
    # Создаем теги
    tags = [
        Tag.objects.get_or_create(name='Новинка', defaults={'slug': 'new'})[0],
        Tag.objects.get_or_create(name='Хит продаж', defaults={'slug': 'bestseller'})[0],
        Tag.objects.get_or_create(name='Распродажа', defaults={'slug': 'sale'})[0],
        Tag.objects.get_or_create(name='Премиум', defaults={'slug': 'premium'})[0],
        Tag.objects.get_or_create(name='Бюджетный', defaults={'slug': 'budget'})[0],
    ]
    
    # Создаем ноутбуки
    print("Создаем ноутбуки...")
    laptops = create_laptops(laptops_category, 24)
    created_laptops = []
    for laptop in laptops:
        laptop.save()
        # Добавляем случайные теги (1-3)
        laptop.tags.set(random.sample(tags, random.randint(1, 3)))
        created_laptops.append(laptop)
    print(f"Создано {len(created_laptops)} ноутбуков")
    
    # Создаем телефоны
    print("Создаем смартфоны...")
    phones = create_phones(phones_category, 24)
    created_phones = []
    for phone in phones:
        phone.save()
        # Добавляем случайные теги (1-3)
        phone.tags.set(random.sample(tags, random.randint(1, 3)))
        created_phones.append(phone)
    print(f"Создано {len(created_phones)} смартфонов")
    
    print(f"\nИтого создано товаров: {len(created_laptops) + len(created_phones)}")
    print("Готово!")


if __name__ == '__main__':
    main()
