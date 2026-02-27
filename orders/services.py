import json
import uuid
import hashlib
import hmac
import requests
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.conf import settings
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


class NowPaymentsGateway(PaymentGateway):
    """
    Интеграция с NowPayments (https://nowpayments.io/)
    Документация IPN: NOWpayments.md
    """

    API_URL = 'https://api.nowpayments.io/v1'

    # Маппинг статусов NowPayments → внутренние статусы Payment
    STATUS_MAP = {
        'waiting': Payment.STATUS_PENDING,
        'confirming': Payment.STATUS_PENDING,
        'confirmed': Payment.STATUS_PENDING,
        'sending': Payment.STATUS_PENDING,
        'partially_paid': Payment.STATUS_PENDING,
        'finished': Payment.STATUS_SUCCEEDED,
        'failed': Payment.STATUS_FAILED,
        'refunded': Payment.STATUS_REFUNDED,
        'expired': Payment.STATUS_FAILED,
    }

    def __init__(self, api_key: str, ipn_callback_url: str = '', success_url: str = '', cancel_url: str = ''):
        self.api_key = api_key
        self.ipn_callback_url = ipn_callback_url
        self.success_url = success_url
        self.cancel_url = cancel_url

    def create_payment(self, amount: Decimal, order_id: int, description: str = "") -> dict:
        url = f'{self.API_URL}/invoice'
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
        }
        payload = {
            'price_amount': float(amount),
            'price_currency': 'rub',
            'order_id': f'order_{order_id}',
            'order_description': description or f'Заказ #{order_id}',
        }
        if self.ipn_callback_url:
            payload['ipn_callback_url'] = self.ipn_callback_url
        if self.success_url:
            payload['success_url'] = self.success_url
        if self.cancel_url:
            payload['cancel_url'] = self.cancel_url

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass
            raise ValidationError(f'NowPayments error: {error_data.get("message", str(e))}')
        except requests.exceptions.RequestException as e:
            raise ValidationError(f'NowPayments connection error: {str(e)}')

        # Ответ содержит поля: id, invoice_url (см. документацию)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning('NowPayments invoice response: %s', data)

        invoice_id = str(data.get('id', ''))
        redirect_url = data.get('invoice_url', '')

        return {
            'payment_id': invoice_id,
            'status': 'pending',
            'redirect_url': redirect_url,
        }

    def refund(self, payment_id: str, amount: Decimal) -> dict:
        """NowPayments не поддерживает возвраты через API — только через личный кабинет."""
        return {
            'refund_id': f'refund_{uuid.uuid4().hex[:12]}',
            'status': 'pending',
        }

    def verify_signature(self, data: dict, signature: str, secret: str) -> bool:
        """
        Проверка IPN-подписи по документации NowPayments:
        1. Сортировать все ключи тела запроса
        2. json.dumps с sort_keys=True
        3. HMAC-SHA512 с IPN Secret
        4. Сравнить с заголовком x-nowpayments-sig
        """
        if not signature or not secret:
            return False

        sorted_body = json.dumps(data, separators=(',', ':'), sort_keys=True)
        expected = hmac.new(
            secret.encode(),
            sorted_body.encode(),
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def map_status(self, nowpayments_status: str) -> str:
        """Перевести статус NowPayments во внутренний статус."""
        return self.STATUS_MAP.get(nowpayments_status, Payment.STATUS_PENDING)


class CryptoCloudGateway(PaymentGateway):
    """
    Интеграция с CryptoCloud (https://cryptocloud.pro/)
    
    Документация API: https://cryptocloud.pro/api/docs
    """
    
    API_URL = 'https://api.cryptocloud.pro'
    
    def __init__(self, api_key: str, secret_key: str, shop_id: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.shop_id = shop_id
    
    def create_payment(self, amount: Decimal, order_id: int, description: str = "") -> dict:
        """
        Создать платёж в CryptoCloud.
        
        Возвращает:
            {
                'payment_id': str,      # ID платежа в CryptoCloud
                'status': 'pending',
                'redirect_url': str,    # URL для перенаправления клиента
            }
        """
        url = f'{self.API_URL}/v1/payment/create'
        
        # Генерируем уникальный order_id для CryptoCloud (наш order_id + префикс)
        crypto_order_id = f'order_{order_id}'
        
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json',
        }
        
        payload = {
            'shop_id': self.shop_id,
            'order_id': crypto_order_id,
            'amount': float(amount),
            'currency': 'RUB',
            'description': description,
            # success_url и fail_url можно добавить при необходимости
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('success'):
                result = data.get('result', {})
                return {
                    'payment_id': result.get('payment_id', crypto_order_id),
                    'status': 'pending',
                    'redirect_url': result.get('url', ''),  # URL страницы оплаты
                }
            else:
                raise ValidationError(f'CryptoCloud error: {data.get("message", "Unknown error")}')
                
        except requests.exceptions.RequestException as e:
            raise ValidationError(f'CryptoCloud connection error: {str(e)}')
    
    def refund(self, payment_id: str, amount: Decimal) -> dict:
        """
        CryptoCloud может не поддерживать возвраты напрямую.
        В этом случае возвращаем заглушку.
        """
        # TODO: Реализовать, если CryptoCloud поддерживает возвраты
        return {
            'refund_id': f'refund_{uuid.uuid4().hex[:12]}',
            'status': 'pending',
        }
    
    def verify_signature(self, data: dict, signature: str, secret: str) -> bool:
        """
        Проверить подпись callback от CryptoCloud.
        
        CryptoCloud использует HMAC-SHA256 подпись.
        Формирование подписи зависит от версии API.
        """
        # CryptoCloud обычно передаёт signature в заголовке или теле
        # Проверка зависит от конкретного формата, который использует CryptoCloud
        # Обычно: sign = HMAC-SHA256(sorted_params, secret_key)
        
        if not signature:
            return False
        
        # Формируем строку для проверки (сортируем ключи)
        payload = "&".join(f"{k}={v}" for k, v in sorted(data.items()))
        expected = hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)


def get_payment_gateway() -> PaymentGateway:
    """Фабрика: возвращает нужный шлюз в зависимости от настроек."""
    gateway_class = getattr(settings, 'PAYMENT_GATEWAY_CLASS', None)
    
    if gateway_class:
        # Явно указан класс шлюза в настройках
        module_path, class_name = gateway_class.rsplit('.', 1)
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)()
    
    # Приоритет: NowPayments > CryptoCloud > Mock
    api_key = getattr(settings, 'NOWPAYMENTS_API_KEY', None)

    if api_key:
        site_url = getattr(settings, 'SITE_URL', '')
        return NowPaymentsGateway(
            api_key=api_key,
            ipn_callback_url=f'{site_url}/orders/payment/callback/' if site_url else '',
            success_url=f'{site_url}/orders/payment/success/' if site_url else '',
            cancel_url=f'{site_url}/orders/payment/cancel/' if site_url else '',
        )
    
    # CryptoCloud (если нет NowPayments)
    cc_api_key = getattr(settings, 'CRYPTOCLOUD_API_KEY', None)
    cc_secret_key = getattr(settings, 'CRYPTOCLOUD_SECRET_KEY', None)
    cc_shop_id = getattr(settings, 'CRYPTOCLOUD_SHOP_ID', None)
    
    if cc_api_key and cc_secret_key and cc_shop_id:
        return CryptoCloudGateway(cc_api_key, cc_secret_key, cc_shop_id)
    
    return MockPaymentGateway()


class PaymentService:

    def __init__(self, gateway: PaymentGateway = None):
        self.gateway = gateway or get_payment_gateway()

    def create_payment(self, order: Order) -> tuple[Payment, str]:
        """
        Создать платёж для заказа.
        
        Возвращает:
            (payment, redirect_url) — кортеж из платежа и URL для перенаправления.
            redirect_url может быть пустым, если перенаправление не требуется.
        
        Бросает ValidationError если заказ уже оплачен.
        """
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
        
        # Получаем redirect_url из ответа шлюза
        redirect_url = gw_response.get('redirect_url', '')
        
        return payment, redirect_url

    def handle_callback(self, data: dict, signature: str, secret: str) -> Payment:
        """Обработать callback от шлюза. Бросает ValidationError при неверной подписи."""
        if not self.gateway.verify_signature(data, signature, secret):
            raise ValidationError('Неверная подпись callback.')

        # NowPayments передаёт payment_id (числовой ID платежа) и payment_status
        # В invoice-flow: invoice_id хранится как наш payment_id
        raw_payment_id = data.get('invoice_id') or data.get('payment_id')
        raw_status = data.get('payment_status') or data.get('status')

        if not raw_payment_id:
            raise ValidationError('Отсутствует payment_id в callback.')

        # Маппинг статусов NowPayments → внутренние
        if isinstance(self.gateway, NowPaymentsGateway):
            status = self.gateway.map_status(raw_status)
        else:
            status = raw_status

        payment_id = str(raw_payment_id)

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
