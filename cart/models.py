from django.db import models
from django.db.models import Sum
from django.conf import settings
from index.models import Product


class DBCart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='db_cart',
        verbose_name='Пользователь',
    )
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        return f'Корзина {self.user.email}'

    def get_total_price(self):
        return sum(item.get_total_price() for item in
                   self.items.select_related('product', 'product__discount'))

    def __bool__(self):
        return True

    def __len__(self):
        result = self.items.aggregate(total=Sum('quantity'))
        return result['total'] or 0


class DBCartItem(models.Model):
    cart = models.ForeignKey(
        DBCart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Товар',
    )
    quantity = models.PositiveIntegerField('Количество', default=1)
    added_at = models.DateTimeField('Добавлен', auto_now_add=True)

    class Meta:
        verbose_name = 'Товар в корзине'
        verbose_name_plural = 'Товары в корзине'
        unique_together = ['cart', 'product']

    def __str__(self):
        return f'{self.product.name} x{self.quantity}'

    def get_total_price(self):
        return self.product.get_final_price() * self.quantity
