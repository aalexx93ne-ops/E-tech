from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import F
from django.contrib import messages
from cart.cart import Cart
from .forms import OrderCreateForm
from .models import Order, OrderItem
from index.models import Stock


def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('cart:cart_detail')
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            cart_items = list(cart)

            # Валидация остатков перед созданием заказа
            product_ids = [item['product'].id for item in cart_items]
            quantities = {item['product'].id: item['quantity'] for item in cart_items}
            stocks = {s.product_id: s.quantity for s in Stock.objects.filter(product_id__in=product_ids)}
            out_of_stock = []
            for item in cart_items:
                pid = item['product'].id
                available = stocks.get(pid, 0)
                if available < quantities[pid]:
                    out_of_stock.append(
                        f"{item['product'].name}: доступно {available}, в корзине {quantities[pid]}"
                    )
            if out_of_stock:
                for msg in out_of_stock:
                    messages.error(request, msg)
                cart_total_price = sum(item['total_price'] for item in cart_items)
                return render(request, 'orders/create.html', {
                    'cart': cart, 'cart_items': cart_items,
                    'cart_total_price': cart_total_price, 'form': form,
                })

            # Создаём заказ атомарно: Order + OrderItems + обновление Stock
            with transaction.atomic():
                order = Order.objects.create(
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data['email'],
                    address=form.cleaned_data['address'],
                    city=form.cleaned_data['city'],
                    user=request.user if request.user.is_authenticated else None,
                )
                OrderItem.objects.bulk_create([
                    OrderItem(
                        order=order,
                        product=item['product'],
                        price=item['price'],
                        quantity=item['quantity'],
                    )
                    for item in cart_items
                ])
                for stock in Stock.objects.select_for_update().filter(product_id__in=product_ids):
                    Stock.objects.filter(pk=stock.pk).update(
                        quantity=F('quantity') - quantities[stock.product_id]
                    )

            cart.clear()
            return redirect('orders:order_success', order_id=order.id)
    else:
        initial = {}
        if request.user.is_authenticated:
            user = request.user
            initial = {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'city': user.city,
                'address': user.address,
            }
        form = OrderCreateForm(initial=initial)

    cart_items = [item for item in cart]
    cart_total_price = sum(item['total_price'] for item in cart_items)
    return render(request, 'orders/create.html', {
        'cart': cart, 'cart_items': cart_items,
        'cart_total_price': cart_total_price, 'form': form,
    })


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/created.html', {'order': order})

import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django_ratelimit.decorators import ratelimit
from .models import Order, Payment
from .services import PaymentService

PAYMENT_SECRET = getattr(settings, 'PAYMENT_CALLBACK_SECRET', 'dev-secret')


@login_required
@ratelimit(key='user', rate='5/m', block=True)
@require_POST
def payment_create(request, order_id):
    order = Order.objects.filter(id=order_id, user=request.user).first()
    if order is None:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()

    service = PaymentService()
    try:
        payment = service.create_payment(order)
    except ValidationError as e:
        messages.error(request, e.message)
        return JsonResponse({'error': e.message}, status=400)

    return JsonResponse({
        'payment_id': payment.payment_id,
        'status': payment.status,
        'redirect_url': f'/orders/{order.id}/payment/status/',
    })


@csrf_exempt
@ratelimit(key='ip', rate='10/m', block=True)
@require_POST
def payment_callback(request):
    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return HttpResponseBadRequest('Invalid JSON')

    signature = request.headers.get('X-Payment-Signature', '')
    service = PaymentService()
    try:
        service.handle_callback(data, signature, PAYMENT_SECRET)
    except ValidationError as e:
        return HttpResponseBadRequest(str(e))

    return JsonResponse({'ok': True})


@login_required
@require_GET
def payment_status(request, order_id):
    order = Order.objects.filter(id=order_id, user=request.user).prefetch_related('payments').first()
    if order is None:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()

    payment = order.payments.first()
    return JsonResponse({
        'order_id': order.id,
        'order_status': order.status,
        'order_paid': order.paid,
        'payment_id': payment.payment_id if payment else None,
        'payment_status': payment.status if payment else None,
    })
