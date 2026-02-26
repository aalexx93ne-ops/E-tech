from django.urls import path
from .views import order_create, order_success, payment_create, payment_callback, payment_status

app_name = 'orders'

urlpatterns = [
    path('create/', order_create, name='order_create'),
    path('success/<int:order_id>/', order_success, name='order_success'),
    path('<int:order_id>/payment/', payment_create, name='payment_create'),
    path('payment/callback/', payment_callback, name='payment_callback'),
    path('<int:order_id>/payment/status/', payment_status, name='payment_status'),
]
