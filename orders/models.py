from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from index.models import Product

class Order(models.Model):
    STATUS_NEW = 'new'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_SHIPPED = 'shipped'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_NEW, 'Новый'),
        (STATUS_CONFIRMED, 'Подтверждён'),
        (STATUS_SHIPPED, 'Отправлен'),
        (STATUS_DELIVERED, 'Доставлен'),
        (STATUS_CANCELLED, 'Отменён'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name='orders',
                             verbose_name="Пользователь")
    first_name = models.CharField(max_length=50, verbose_name="Имя")
    last_name = models.CharField(max_length=50, verbose_name="Фамилия")
    email = models.EmailField(verbose_name="Email")
    address = models.CharField(max_length=250, verbose_name="Адрес")
    city = models.CharField(max_length=100, verbose_name="Город")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated = models.DateTimeField(auto_now=True, verbose_name="Обновлен")
    paid = models.BooleanField(default=False, verbose_name="Оплачен")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_NEW, verbose_name="Статус")

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self):
        return f'Заказ {self.id}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name="Заказ")
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE, verbose_name="Товар")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity


class Payment(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = [
        (STATUS_PENDING,   'Ожидает'),
        (STATUS_SUCCEEDED, 'Успешно'),
        (STATUS_FAILED,    'Ошибка'),
        (STATUS_CANCELLED, 'Отменён'),
        (STATUS_REFUNDED,  'Возврат'),
    ]

    # Допустимые переходы статусов
    ALLOWED_TRANSITIONS = {
        STATUS_PENDING:   {STATUS_SUCCEEDED, STATUS_FAILED, STATUS_CANCELLED},
        STATUS_SUCCEEDED: {STATUS_REFUNDED},
        STATUS_FAILED:    set(),
        STATUS_CANCELLED: set(),
        STATUS_REFUNDED:  set(),
    }

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='payments',
        verbose_name='Заказ',
    )
    payment_id = models.CharField(
        max_length=100, unique=True, verbose_name='ID платежа в шлюзе',
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='Сумма',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_PENDING, verbose_name='Статус',
    )
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']

    def __str__(self):
        return f'Платёж {self.payment_id} ({self.get_status_display()})'

    def transition_to(self, new_status):
        """Перевести платёж в новый статус с валидацией перехода."""
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(
                f'Переход {self.status} → {new_status} недопустим.'
            )
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
