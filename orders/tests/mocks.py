import hashlib
import hmac
import uuid
from decimal import Decimal
from orders.services import PaymentGateway


class MockPaymentGateway(PaymentGateway):
    """Заглушка для тестов — никаких реальных HTTP-запросов."""

    # Можно настроить поведение перед тестом
    fail_on_create = False
    timeout_on_create = False

    def create_payment(self, amount: Decimal, order_id: int, description: str = "") -> dict:
        if self.timeout_on_create:
            raise ConnectionError('Gateway timeout')
        if self.fail_on_create:
            return {
                'payment_id': f'pay_{uuid.uuid4().hex[:12]}',
                'status': 'failed',
                'redirect_url': '',
            }
        return {
            'payment_id': f'mock_{uuid.uuid4().hex[:12]}',
            'status': 'pending',
            'redirect_url': f'/mock-pay/?order={order_id}',
        }

    def refund(self, payment_id: str, amount: Decimal) -> dict:
        return {
            'refund_id': f'refund_{uuid.uuid4().hex[:12]}',
            'status': 'succeeded',
        }

    def verify_signature(self, data: dict, signature: str, secret: str) -> bool:
        payload = "&".join(f"{k}={v}" for k, v in sorted(data.items()))
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


def make_valid_signature(data: dict, secret: str) -> str:
    payload = "&".join(f"{k}={v}" for k, v in sorted(data.items()))
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
