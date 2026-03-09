from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0010_populate_comparison_metrics'),
    ]

    operations = [
        # Добавляем поля в SpecificationType
        migrations.AddField(
            model_name='specificationtype',
            name='category_map',
            field=models.JSONField(blank=True, default=dict, help_text='{"OLED": 100, "IPS": 70, "TN": 40}', verbose_name='Карта значений для categorical'),
        ),
        migrations.AddField(
            model_name='specificationtype',
            name='comparison_type',
            field=models.CharField(choices=[('higher_better', 'Чем больше — тем лучше'), ('lower_better', 'Чем меньше — тем лучше'), ('categorical', 'Категориальное сравнение'), ('boolean', 'Булево сравнение')], default='higher_better', max_length=20, verbose_name='Тип сравнения'),
        ),
        migrations.AddField(
            model_name='specificationtype',
            name='is_comparable',
            field=models.BooleanField(default=True, help_text='Если False — не показывать в таблице сравнения', verbose_name='Участвует в сравнении'),
        ),
        migrations.AddField(
            model_name='specificationtype',
            name='priority',
            field=models.PositiveSmallIntegerField(default=50, help_text='1-100, чем больше — тем выше в списке', verbose_name='Приоритет в сравнении'),
        ),
        migrations.AddField(
            model_name='specificationtype',
            name='unit',
            field=models.CharField(blank=True, help_text='ГБ, г, мм, дюймов', max_length=50, verbose_name='Единица измерения'),
        ),
        migrations.AddIndex(
            model_name='specificationtype',
            index=models.Index(fields=['is_comparable', '-priority'], name='index_speci_is_comp_304230_idx'),
        ),
    ]
