import json
import hashlib, hmac
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from orders.models import Order, Payment
from orders.tests.fixtures import make_user, make_order_with_items, make_payment
from orders.tests.mocks import MockPaymentGateway, make_valid_signature

User = get_user_model()
SECRET = 'dev-secret'


class PaymentCreateViewTest(TestCase):
    """4.3.1 / 4.3.2 Страница создания платежа."""

    def setUp(self):
        self.user = make_user()
        self.other = make_user('other', 'other@test.com')
        self.order = make_order_with_items(user=self.user)

    def _url(self):
        return reverse('orders:payment_create', kwargs={'order_id': self.order.id})

    def test_anonymous_redirects_to_login(self):
        response = self.client.post(self._url())
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_owner_creates_payment(self):
        self.client.force_login(self.user)
        with self.settings(PAYMENT_GATEWAY_CLASS=None):
            response = self.client.post(self._url())
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('payment_id', data)
        self.assertTrue(Payment.objects.filter(order=self.order).exists())

    def test_other_user_forbidden(self):
        self.client.force_login(self.other)
        response = self.client.post(self._url())
        self.assertEqual(response.status_code, 403)

    def test_double_payment_returns_400(self):
        self.client.force_login(self.user)
        with self.settings(PAYMENT_GATEWAY_CLASS=None):
            self.client.post(self._url())         # первый раз
            response = self.client.post(self._url())  # второй раз
        self.assertEqual(response.status_code, 400)

    def test_paid_order_returns_400(self):
        self.order.paid = True
        self.order.save()
        self.client.force_login(self.user)
        response = self.client.post(self._url())
        self.assertEqual(response.status_code, 400)


class PaymentCallbackViewTest(TestCase):
    """4.3.3 Callback от платёжной системы."""

    def setUp(self):
        self.user = make_user()
        self.order = make_order_with_items(user=self.user)
        self.payment = make_payment(self.order)
        self.url = reverse('orders:payment_callback')

    def _post(self, data, secret=SECRET):
        sig = make_valid_signature(data, secret)
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_X_PAYMENT_SIGNATURE=sig,
        )

    def test_valid_callback_succeeded(self):
        response = self._post({
            'payment_id': self.payment.payment_id,
            'status': 'succeeded',
        })
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_SUCCEEDED)

    def test_invalid_signature_returns_400(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'payment_id': self.payment.payment_id, 'status': 'succeeded'}),
            content_type='application/json',
            HTTP_X_PAYMENT_SIGNATURE='bad_sig',
        )
        self.assertEqual(response.status_code, 400)

    def test_idempotent_repeated_callback(self):
        self._post({'payment_id': self.payment.payment_id, 'status': 'succeeded'})
        self._post({'payment_id': self.payment.payment_id, 'status': 'succeeded'})
        self.assertEqual(
            Payment.objects.filter(order=self.order, status=Payment.STATUS_SUCCEEDED).count(), 1
        )

    def test_invalid_json_returns_400(self):
        response = self.client.post(self.url, data='not json', content_type='application/json')
        self.assertEqual(response.status_code, 400)


class PaymentStatusViewTest(TestCase):
    """4.3.4 Статус платежа."""

    def setUp(self):
        self.user = make_user()
        self.other = make_user('other2', 'other2@test.com')
        self.order = make_order_with_items(user=self.user)
        self.payment = make_payment(self.order)

    def _url(self):
        return reverse('orders:payment_status', kwargs={'order_id': self.order.id})

    def test_owner_sees_status(self):
        self.client.force_login(self.user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['order_id'], self.order.id)
        self.assertEqual(data['payment_status'], Payment.STATUS_PENDING)

    def test_other_user_forbidden(self):
        self.client.force_login(self.other)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirects(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 302)

    def test_no_payment_returns_null(self):
        order2 = make_order_with_items(user=self.user)
        self.client.force_login(self.user)
        url = reverse('orders:payment_status', kwargs={'order_id': order2.id})
        response = self.client.get(url)
        data = json.loads(response.content)
        self.assertIsNone(data['payment_id'])
        self.assertIsNone(data['payment_status'])
