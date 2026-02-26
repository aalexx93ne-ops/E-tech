import uuid
import hashlib
import hmac
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Order, Payment


class PaymentGateway:
    """Абстракция платёжного шлюза. В проде заменяется реальной реализацией."""

    def create_payment(self, amount: Decimal, order_id: int, description: str = "") -> dict:
        """Создать платёж в шлюзе. Возвращает {'payment_id': str, 'status': str, 'redirect_url': str}."""
        raise NotImplementedError

    def refund(self, payment_id: str, amount: Decimal) -> dict:
        """Запросить возврат. Возвращает {'refund_id': str, 'status': str}."""
        raise NotImplementedError

    def verify_signature(self, data: dict, signature: str, secret: str) -> bool:
        """Проверить подпись callback от шлюза."""
        raise NotImplementedError


class MockPaymentGateway(PaymentGateway):
    """Заглушка для тестов и разработки."""

    def create_payment(self, amount, order_id, description=""):
        return {
            'payment_id': f'mock_{uuid.uuid4().hex[:12]}',
            'status': 'pending',
            'redirect_url': f'/orders/mock-pay/?order={order_id}',
        }

    def refund(self, payment_id, amount):
        return {
            'refund_id': f'refund_{uuid.uuid4().hex[:12]}',
            'status': 'succeeded',
        }

    def verify_signature(self, data: dict, signature: str, secret: str) -> bool:
        payload = "&".join(f"{k}={v}" for k, v in sorted(data.items()))
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


def get_payment_gateway() -> PaymentGateway:
    """Фабрика: возвращает нужный шлюз в зависимости от настроек."""
    from django.conf import settings
    gateway_class = getattr(settings, 'PAYMENT_GATEWAY_CLASS', None)
    if gateway_class is None:
        return MockPaymentGateway()
    module_path, class_name = gateway_class.rsplit('.', 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


class PaymentService:

    def __init__(self, gateway: PaymentGateway = None):
        self.gateway = gateway or get_payment_gateway()

    def create_payment(self, order: Order) -> Payment:
        """Создать платёж для заказа. Бросает ValidationError если заказ уже оплачен."""
        if order.paid:
            raise ValidationError('Заказ уже оплачен.')
        if order.payments.filter(status=Payment.STATUS_PENDING).exists():
            raise ValidationError('Для этого заказа уже есть активный платёж.')

        amount = order.get_total_cost()
        if amount <= 0:
            raise ValidationError('Сумма заказа должна быть больше нуля.')

        gw_response = self.gateway.create_payment(
            amount=amount,
            order_id=order.id,
            description=f'Заказ #{order.id}',
        )

        payment = Payment.objects.create(
            order=order,
            payment_id=gw_response['payment_id'],
            amount=amount,
            status=Payment.STATUS_PENDING,
        )
        return payment

    def handle_callback(self, data: dict, signature: str, secret: str) -> Payment:
        """Обработать callback от шлюза. Бросает ValidationError при неверной подписи."""
        if not self.gateway.verify_signature(data, signature, secret):
            raise ValidationError('Неверная подпись callback.')

        payment_id = data.get('payment_id')
        status = data.get('status')

        try:
            payment = Payment.objects.select_for_update().get(payment_id=payment_id)
        except Payment.DoesNotExist:
            raise ValidationError(f'Платёж {payment_id} не найден.')

        # Идемпотентность: если статус уже установлен — не меняем
        if payment.status == status:
            return payment

        with transaction.atomic():
            payment.transition_to(status)
            if status == Payment.STATUS_SUCCEEDED:
                order = payment.order
                order.paid = True
                order.status = Order.STATUS_CONFIRMED
                order.save(update_fields=['paid', 'status', 'updated'])
            elif status == Payment.STATUS_FAILED:
                if data.get('error_message'):
                    payment.error_message = data['error_message']
                    payment.save(update_fields=['error_message', 'updated_at'])

        return payment

    def refund_payment(self, payment: Payment) -> Payment:
        """Выполнить возврат по платежу."""
        if payment.status != Payment.STATUS_SUCCEEDED:
            raise ValidationError('Возврат возможен только для успешных платежей.')

        self.gateway.refund(payment.payment_id, payment.amount)

        with transaction.atomic():
            payment.transition_to(Payment.STATUS_REFUNDED)
            order = payment.order
            order.paid = False
            order.status = Order.STATUS_CANCELLED
            order.save(update_fields=['paid', 'status', 'updated'])

        return payment
