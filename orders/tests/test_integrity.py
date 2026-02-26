import threading
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.core.exceptions import ValidationError

from orders.models import Order, Payment
from orders.services import PaymentService
from orders.tests.fixtures import make_order_with_items, make_payment
from orders.tests.mocks import MockPaymentGateway, make_valid_signature

SECRET = 'dev-secret'


class PaymentTransactionAtomicityTest(TestCase):
    """4.5.1 Атомарность — сбой откатывает все изменения."""

    def test_failed_callback_does_not_partially_update(self):
        """Если callback упал в середине — Order не должен быть изменён."""
        gateway = MockPaymentGateway()
        service = PaymentService(gateway=gateway)
        order = make_order_with_items()
        payment = service.create_payment(order)

        from unittest.mock import patch
        # Имитируем сбой при сохранении Order после успешного payment.transition_to
        original_save = Order.save
        call_count = [0]

        def failing_save(self_order, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception('DB failure')
            return original_save(self_order, *args, **kwargs)

        data = {'payment_id': payment.payment_id, 'status': 'succeeded'}
        sig = make_valid_signature(data, SECRET)

        with patch.object(Order, 'save', failing_save):
            try:
                service.handle_callback(data, sig, SECRET)
            except Exception:
                pass

        # Payment откатился обратно в pending (из-за atomic)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PENDING)
        order.refresh_from_db()
        self.assertFalse(order.paid)

    def test_no_hanging_payments_on_gateway_error(self):
        """При ошибке шлюза платёж не создаётся в БД."""
        gateway = MockPaymentGateway()
        gateway.timeout_on_create = True
        service = PaymentService(gateway=gateway)
        order = make_order_with_items()

        try:
            service.create_payment(order)
        except ConnectionError:
            pass

        self.assertEqual(Payment.objects.filter(order=order).count(), 0)


class OrderLockingTest(TestCase):
    """4.5.2 Блокировка заказа при оплате."""

    def test_cannot_create_two_pending_payments(self):
        gateway = MockPaymentGateway()
        service = PaymentService(gateway=gateway)
        order = make_order_with_items()

        service.create_payment(order)
        with self.assertRaises(ValidationError):
            service.create_payment(order)

    def test_can_create_payment_after_previous_failed(self):
        gateway = MockPaymentGateway()
        service = PaymentService(gateway=gateway)
        order = make_order_with_items()

        p1 = service.create_payment(order)
        data = {'payment_id': p1.payment_id, 'status': 'failed'}
        sig = make_valid_signature(data, SECRET)
        service.handle_callback(data, sig, SECRET)

        # Теперь нет активного pending — можно создать новый
        p2 = service.create_payment(order)
        self.assertNotEqual(p1.payment_id, p2.payment_id)
        self.assertEqual(p2.status, Payment.STATUS_PENDING)

    def test_payment_id_globally_unique(self):
        """payment_id уникален на уровне БД."""
        order = make_order_with_items()
        make_payment(order, payment_id='pay_dup')
        with self.assertRaises(Exception):
            make_payment(order, payment_id='pay_dup')
