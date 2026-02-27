from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from orders.models import Order, Payment
from orders.tests.fixtures import make_order_with_items, make_payment


class PaymentCreationTest(TestCase):
    """4.1.1 Создание платежа."""

    def setUp(self):
        self.order = make_order_with_items(price='3000.00', quantity=2)

    def test_payment_created_with_pending_status(self):
        payment = make_payment(self.order)
        self.assertEqual(payment.status, Payment.STATUS_PENDING)

    def test_payment_amount_equals_order_total(self):
        payment = make_payment(self.order)
        self.assertEqual(payment.amount, self.order.get_total_cost())

    def test_payment_linked_to_order(self):
        payment = make_payment(self.order)
        self.assertEqual(payment.order, self.order)

    def test_order_starts_with_new_status(self):
        self.assertEqual(self.order.status, Order.STATUS_NEW)
        self.assertFalse(self.order.paid)

    def test_payment_id_unique(self):
        p1 = make_payment(self.order, payment_id='pay_001')
        with self.assertRaises(Exception):
            make_payment(self.order, payment_id='pay_001')


class PaymentStatusTransitionTest(TestCase):
    """4.1.2 Переходы статусов платежа."""

    def setUp(self):
        self.order = make_order_with_items()

    def test_pending_to_succeeded(self):
        payment = make_payment(self.order)
        payment.transition_to(Payment.STATUS_SUCCEEDED)
        self.assertEqual(payment.status, Payment.STATUS_SUCCEEDED)

    def test_pending_to_failed(self):
        payment = make_payment(self.order)
        payment.transition_to(Payment.STATUS_FAILED)
        self.assertEqual(payment.status, Payment.STATUS_FAILED)

    def test_pending_to_cancelled(self):
        payment = make_payment(self.order)
        payment.transition_to(Payment.STATUS_CANCELLED)
        self.assertEqual(payment.status, Payment.STATUS_CANCELLED)

    def test_succeeded_to_refunded(self):
        payment = make_payment(self.order, status=Payment.STATUS_SUCCEEDED)
        payment.transition_to(Payment.STATUS_REFUNDED)
        self.assertEqual(payment.status, Payment.STATUS_REFUNDED)

    def test_failed_to_succeeded_forbidden(self):
        payment = make_payment(self.order, status=Payment.STATUS_FAILED)
        with self.assertRaises(ValidationError):
            payment.transition_to(Payment.STATUS_SUCCEEDED)

    def test_cancelled_to_pending_forbidden(self):
        payment = make_payment(self.order, status=Payment.STATUS_CANCELLED)
        with self.assertRaises(ValidationError):
            payment.transition_to(Payment.STATUS_PENDING)

    def test_refunded_to_succeeded_forbidden(self):
        payment = make_payment(self.order, status=Payment.STATUS_REFUNDED)
        with self.assertRaises(ValidationError):
            payment.transition_to(Payment.STATUS_SUCCEEDED)

    def test_transition_persisted_to_db(self):
        payment = make_payment(self.order)
        payment.transition_to(Payment.STATUS_SUCCEEDED)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_SUCCEEDED)


class DoublePaymentPreventionTest(TestCase):
    """4.1.3 Защита от повторной оплаты."""

    def setUp(self):
        self.order = make_order_with_items()

    def test_cannot_create_payment_for_paid_order(self):
        from orders.services import PaymentService
        from orders.tests.mocks import MockPaymentGateway
        self.order.paid = True
        self.order.save()
        service = PaymentService(gateway=MockPaymentGateway())
        with self.assertRaises(ValidationError):
            service.create_payment(self.order)

    def test_cannot_create_second_pending_payment(self):
        from orders.services import PaymentService
        from orders.tests.mocks import MockPaymentGateway
        service = PaymentService(gateway=MockPaymentGateway())
        service.create_payment(self.order)
        with self.assertRaises(ValidationError):
            service.create_payment(self.order)


class PaymentAmountTest(TestCase):
    """4.1.4 Сумма платежа."""

    def test_amount_matches_order_total(self):
        order = make_order_with_items(price='4999.00', quantity=3)
        payment = make_payment(order)
        self.assertEqual(payment.amount, Decimal('14997.00'))

    def test_amount_matches_multiline_order(self):
        from index.models import Product, Category, Brand
        from orders.models import OrderItem
        from orders.tests.fixtures import make_order
        cat, _ = Category.objects.get_or_create(name='Тест', slug='test')
        brand, _ = Brand.objects.get_or_create(name='BrandX', slug='brandx')
        p1 = Product.objects.create(name='A', slug='aaa', price=Decimal('1000'), category=cat, brand=brand)
        p2 = Product.objects.create(name='B', slug='bbb', price=Decimal('2500'), category=cat, brand=brand)
        order = make_order()
        OrderItem.objects.create(order=order, product=p1, price=Decimal('1000'), quantity=2)
        OrderItem.objects.create(order=order, product=p2, price=Decimal('2500'), quantity=1)
        payment = make_payment(order)
        self.assertEqual(payment.amount, Decimal('4500.00'))


class PaymentOrderStatusSyncTest(TestCase):
    """4.1.5 Обновление статуса заказа при оплате."""

    def setUp(self):
        self.order = make_order_with_items()

    def _handle(self, status, error_message=''):
        from orders.services import PaymentService
        from orders.tests.mocks import MockPaymentGateway, make_valid_signature
        from django.conf import settings
        secret = getattr(settings, 'PAYMENT_CALLBACK_SECRET', 'dev-secret')
        service = PaymentService(gateway=MockPaymentGateway())
        payment, _ = service.create_payment(self.order)
        data = {'payment_id': payment.payment_id, 'status': status}
        if error_message:
            data['error_message'] = error_message
        sig = make_valid_signature(data, secret)
        return service.handle_callback(data, sig, secret)

    def test_succeeded_marks_order_paid_and_confirmed(self):
        self._handle(Payment.STATUS_SUCCEEDED)
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)
        self.assertEqual(self.order.status, Order.STATUS_CONFIRMED)

    def test_failed_leaves_order_new_and_unpaid(self):
        self._handle(Payment.STATUS_FAILED)
        self.order.refresh_from_db()
        self.assertFalse(self.order.paid)
        self.assertEqual(self.order.status, Order.STATUS_NEW)

    def test_failed_stores_error_message(self):
        self._handle(Payment.STATUS_FAILED, error_message='Insufficient funds')
        payment = self.order.payments.first()
        self.assertIn('Insufficient funds', payment.error_message)
