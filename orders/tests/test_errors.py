from django.test import TestCase
from django.core.exceptions import ValidationError

from orders.models import Order, Payment
from orders.services import PaymentService
from orders.tests.fixtures import make_order_with_items, make_payment
from orders.tests.mocks import MockPaymentGateway, make_valid_signature

SECRET = 'dev-secret'


class GatewayTimeoutTest(TestCase):
    """4.4.1 Таймаут платёжной системы."""

    def test_timeout_does_not_create_payment(self):
        gateway = MockPaymentGateway()
        gateway.timeout_on_create = True
        service = PaymentService(gateway=gateway)
        order = make_order_with_items()
        with self.assertRaises(ConnectionError):
            service.create_payment(order)
        self.assertEqual(order.payments.count(), 0)

    def test_order_stays_new_after_timeout(self):
        gateway = MockPaymentGateway()
        gateway.timeout_on_create = True
        service = PaymentService(gateway=gateway)
        order = make_order_with_items()
        try:
            service.create_payment(order)
        except ConnectionError:
            pass
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_NEW)
        self.assertFalse(order.paid)

    def test_can_retry_after_timeout(self):
        """После таймаута можно создать платёж снова."""
        gateway = MockPaymentGateway()
        service = PaymentService(gateway=gateway)
        order = make_order_with_items()
        gateway.timeout_on_create = True
        try:
            service.create_payment(order)
        except ConnectionError:
            pass
        gateway.timeout_on_create = False
        payment = service.create_payment(order)
        self.assertEqual(payment.status, Payment.STATUS_PENDING)


class InsufficientFundsTest(TestCase):
    """4.4.2 Недостаточно средств — имитируется через callback с failed."""

    def setUp(self):
        self.gateway = MockPaymentGateway()
        self.service = PaymentService(gateway=self.gateway)
        self.order = make_order_with_items()
        self.payment = self.service.create_payment(self.order)

    def test_failed_callback_leaves_order_unchanged(self):
        data = {
            'payment_id': self.payment.payment_id,
            'status': 'failed',
            'error_message': 'Insufficient funds',
        }
        sig = make_valid_signature(data, SECRET)
        self.service.handle_callback(data, sig, SECRET)

        self.order.refresh_from_db()
        self.assertFalse(self.order.paid)
        self.assertEqual(self.order.status, Order.STATUS_NEW)

    def test_failed_payment_stores_error(self):
        data = {
            'payment_id': self.payment.payment_id,
            'status': 'failed',
            'error_message': 'Insufficient funds',
        }
        sig = make_valid_signature(data, SECRET)
        self.service.handle_callback(data, sig, SECRET)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_FAILED)
        self.assertIn('Insufficient funds', self.payment.error_message)

    def test_can_create_new_payment_after_failure(self):
        """После неудачного платежа можно создать новый."""
        data = {'payment_id': self.payment.payment_id, 'status': 'failed'}
        sig = make_valid_signature(data, SECRET)
        self.service.handle_callback(data, sig, SECRET)

        new_payment = self.service.create_payment(self.order)
        self.assertNotEqual(new_payment.payment_id, self.payment.payment_id)
        self.assertEqual(new_payment.status, Payment.STATUS_PENDING)


class UserCancelTest(TestCase):
    """4.4.3 Отмена пользователем."""

    def setUp(self):
        self.gateway = MockPaymentGateway()
        self.service = PaymentService(gateway=self.gateway)
        self.order = make_order_with_items()
        self.payment = self.service.create_payment(self.order)

    def test_cancelled_payment_status(self):
        data = {'payment_id': self.payment.payment_id, 'status': 'cancelled'}
        sig = make_valid_signature(data, SECRET)
        self.service.handle_callback(data, sig, SECRET)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_CANCELLED)

    def test_order_stays_new_after_cancel(self):
        data = {'payment_id': self.payment.payment_id, 'status': 'cancelled'}
        sig = make_valid_signature(data, SECRET)
        self.service.handle_callback(data, sig, SECRET)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_NEW)
        self.assertFalse(self.order.paid)

    def test_can_create_new_payment_after_cancel(self):
        data = {'payment_id': self.payment.payment_id, 'status': 'cancelled'}
        sig = make_valid_signature(data, SECRET)
        self.service.handle_callback(data, sig, SECRET)

        new_payment = self.service.create_payment(self.order)
        self.assertEqual(new_payment.status, Payment.STATUS_PENDING)
