from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0008_alter_review_options_review_is_verified_purchase_and_more'),
    ]

    operations = [
        # Пустая миграция-заглушка для восстановления цепочки зависимостей
        # Оригинальная миграция должна была заполнять данные ComparisonMetric,
        # но модели были удалены в 0011
    ]
