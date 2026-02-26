from django.db import transaction
from django.db.models import F
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Order
from index.models import Stock


@receiver(pre_save, sender=Order)
def restore_stock_on_cancel(sender, instance, **kwargs):
    """Возвращает остатки на склад при переводе заказа в статус cancelled."""
    if not instance.pk:
        return  # новый заказ — ничего не делаем

    try:
        previous = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    if previous.status == instance.status:
        return  # статус не изменился
    if instance.status != Order.STATUS_CANCELLED:
        return  # отменяем только при переходе в cancelled
    if previous.status == Order.STATUS_CANCELLED:
        return  # уже был отменён — не возвращаем дважды

    quantities = {
        item.product_id: item.quantity
        for item in instance.items.all()
    }
    with transaction.atomic():
        for stock in Stock.objects.select_for_update().filter(product_id__in=quantities):
            Stock.objects.filter(pk=stock.pk).update(
                quantity=F('quantity') + quantities[stock.product_id]
            )
