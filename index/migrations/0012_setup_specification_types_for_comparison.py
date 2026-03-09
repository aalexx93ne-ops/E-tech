from django.db import migrations


def setup_spec_types_for_comparison(apps, schema_editor):
    """Настраивает SpecificationType для системы сравнения."""
    SpecificationType = apps.get_model('index', 'SpecificationType')
    
    # Конфигурация для различных типов характеристик
    config = {
        # Смартфоны и ноутбуки - общие
        'оперативная память': {
            'comparison_type': 'higher_better',
            'unit': 'ГБ',
            'priority': 10,
        },
        'озу': {
            'comparison_type': 'higher_better',
            'unit': 'ГБ',
            'priority': 10,
        },
        'память': {
            'comparison_type': 'higher_better',
            'unit': 'ГБ',
            'priority': 9,
        },
        'встроенная память': {
            'comparison_type': 'higher_better',
            'unit': 'ГБ',
            'priority': 9,
        },
        'накопитель': {
            'comparison_type': 'higher_better',
            'unit': 'ГБ',
            'priority': 9,
        },
        'диагональ экрана': {
            'comparison_type': 'higher_better',
            'unit': 'дюймов',
            'priority': 12,
        },
        'экран': {
            'comparison_type': 'higher_better',
            'unit': '',
            'priority': 8,
        },
        'тип экрана': {
            'comparison_type': 'categorical',
            'unit': '',
            'priority': 15,
            'category_map': {'AMOLED': 100, 'OLED': 95, 'IPS': 70, 'TN': 40},
        },
        'батарея': {
            'comparison_type': 'higher_better',
            'unit': 'мАч',
            'priority': 8,
        },
        'аккумулятор': {
            'comparison_type': 'higher_better',
            'unit': 'мАч',
            'priority': 8,
        },
        'быстрая зарядка': {
            'comparison_type': 'higher_better',
            'unit': 'W',
            'priority': 6,
        },
        'камера': {
            'comparison_type': 'higher_better',
            'unit': 'MP',
            'priority': 7,
        },
        'видеокарта': {
            'comparison_type': 'higher_better',
            'unit': '',
            'priority': 11,
        },
        'процессор': {
            'comparison_type': 'higher_better',
            'unit': '',
            'priority': 11,
        },
        'частота обновления': {
            'comparison_type': 'higher_better',
            'unit': 'Гц',
            'priority': 7,
        },
        'сеть': {
            'comparison_type': 'categorical',
            'unit': '',
            'priority': 5,
            'category_map': {'5G': 100, '4G': 50, '3G': 20},
        },
        'ос': {
            'comparison_type': 'categorical',
            'unit': '',
            'priority': 4,
            'category_map': {'Windows 11': 90, 'Windows 10': 70, 'macOS': 85, 'Linux': 60, 'Android': 50, 'iOS': 80},
        },
    }
    
    for slug, settings in config.items():
        spec_type = SpecificationType.objects.filter(
            name__icontains=slug
        ).first()
        
        if spec_type:
            spec_type.comparison_type = settings['comparison_type']
            spec_type.unit = settings['unit']
            spec_type.priority = settings['priority']
            spec_type.is_comparable = True
            
            if 'category_map' in settings:
                spec_type.category_map = settings['category_map']
            
            spec_type.save()
            print(f"Updated: {spec_type.name}")


def reverse_setup(apps, schema_editor):
    """Сбрасывает настройки сравнения."""
    SpecificationType = apps.get_model('index', 'SpecificationType')
    SpecificationType.objects.update(
        comparison_type='higher_better',
        priority=50,
        unit='',
        category_map={},
        is_comparable=True
    )


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0011_alter_comparisonmetric_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(setup_spec_types_for_comparison, reverse_setup),
    ]
