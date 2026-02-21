from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from cart.models import DBCart


class Command(BaseCommand):
    help = 'Удаляет корзины, не обновлявшиеся более 90 дней'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Количество дней неактивности (по умолчанию 90)',
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)
        old_carts = DBCart.objects.filter(updated_at__lt=cutoff)
        count = old_carts.count()
        old_carts.delete()
        self.stdout.write(
            self.style.SUCCESS(f'Удалено корзин: {count} (старше {days} дней)')
        )
