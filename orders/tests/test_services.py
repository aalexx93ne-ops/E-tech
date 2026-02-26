from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from orders.models import Order, Payment
from orders.services import PaymentService
from orders.tests.fixtures import make_order, make_order_with_items, make_payment
from orders.tests.mocks import MockPaymentGateway, make_valid_signature

SECRET = 'dev-secret'


class PaymentServiceCreateTest(TestCase):
    """4.2.1 Создание платежа через сервис."""

    def setUp(self):
        self.gateway = MockPaymentGateway()
        self.service = PaymentService(gateway=self.gateway)
        self.order = make_order_with_items(price='7500.00', quantity=2)

    def test_creates_payment_with_unique_id(self):
        payment = self.service.create_payment(self.order)
        self.assertTrue(payment.payment_id.startswith('mock_'))
        self.assertNotEqual(payment.payment_id, '')

    def test_payment_amount_matches_order(self):
        payment = self.service.create_payment(self.order)
        self.assertEqual(payment.amount, self.order.get_total_cost())

    def test_payment_status_is_pending(self):
        payment = self.service.create_payment(self.order)
        self.assertEqual(payment.status, Payment.STATUS_PENDING)

    def test_payment_saved_to_db(self):
        payment = self.service.create_payment(self.order)
        self.assertTrue(Payment.objects.filter(pk=payment.pk).exists())

    def test_raises_for_paid_order(self):
        self.order.paid = True
        self.order.save()
        with self.assertRaises(ValidationError):
            self.service.create_payment(self.order)

    def test_raises_for_zero_amount_order(self):
        empty_order = make_order()
        with self.assertRaises(ValidationError):
            self.service.create_payment(empty_order)


class PaymentCallbackTest(TestCase):
    """4.2.2 Обработка callback."""

    def setUp(self):
        self.gateway = MockPaymentGateway()
        self.service = PaymentService(gateway=self.gateway)
        self.order = make_order_with_items()
        self.payment = self.service.create_payment(self.order)

    def _callback(self, status, extra=None):
        data = {'payment_id': self.payment.payment_id, 'status': status}
        if extra:
            data.update(extra)
        sig = make_valid_signature(data, SECRET)
        return self.service.handle_callback(data, sig, SECRET)

    def test_succeeded_updates_payment(self):
        self._callback(Payment.STATUS_SUCCEEDED)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_SUCCEEDED)

    def test_succeeded_marks_order_paid(self):
        self._callback(Payment.STATUS_SUCCEEDED)
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)
        self.assertEqual(self.order.status, Order.STATUS_CONFIRMED)

    def test_failed_updates_payment(self):
        self._callback(Payment.STATUS_FAILED)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_FAILED)

    def test_failed_does_not_change_order(self):
        self._callback(Payment.STATUS_FAILED)
        self.order.refresh_from_db()
        self.assertFalse(self.order.paid)
        self.assertEqual(self.order.status, Order.STATUS_NEW)

    def test_invalid_signature_raises(self):
        data = {'payment_id': self.payment.payment_id, 'status': 'succeeded'}
        with self.assertRaises(ValidationError):
            self.service.handle_callback(data, 'bad_signature', SECRET)

    def test_idempotent_callback(self):
        """Повторный callback с тем же статусом не меняет данные."""
        self._callback(Payment.STATUS_SUCCEEDED)
        self._callback(Payment.STATUS_SUCCEEDED)  # второй раз
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)

    def test_unknown_payment_id_raises(self):
        data = {'payment_id': 'nonexistent_id', 'status': 'succeeded'}
        sig = make_valid_signature(data, SECRET)
        with self.assertRaises(ValidationError):
            self.service.handle_callback(data, sig, SECRET)


class PaymentRefundTest(TestCase):
    """4.2.3 Возврат средств."""

    def setUp(self):
        self.gateway = MockPaymentGateway()
        self.service = PaymentService(gateway=self.gateway)
        self.order = make_order_with_items(price='3000.00', quantity=1)
        self.payment = make_payment(self.order, status=Payment.STATUS_SUCCEEDED)
        self.order.paid = True
        self.order.status = Order.STATUS_CONFIRMED
        self.order.save()

    def test_refund_changes_payment_status(self):
        self.service.refund_payment(self.payment)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_REFUNDED)

    def test_refund_marks_order_cancelled(self):
        self.service.refund_payment(self.payment)
        self.order.refresh_from_db()
        self.assertFalse(self.order.paid)
        self.assertEqual(self.order.status, Order.STATUS_CANCELLED)

    def test_refund_amount_matches_payment(self):
        """Сумма возврата совпадает с суммой платежа."""
        original_amount = self.payment.amount
        self.service.refund_payment(self.payment)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.amount, original_amount)

    def test_cannot_refund_pending_payment(self):
        pending = make_payment(self.order, payment_id='pay_extra_001')
        with self.assertRaises(ValidationError):
            self.service.refund_payment(pending)

    def test_cannot_refund_failed_payment(self):
        failed = make_payment(self.order, status=Payment.STATUS_FAILED, payment_id='pay_extra_002')
        with self.assertRaises(ValidationError):
            self.service.refund_payment(failed)
