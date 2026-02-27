import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django_ratelimit.decorators import ratelimit

from cart.cart import Cart
from index.models import Stock
from .forms import OrderCreateForm
from .models import Order, OrderItem, Payment
from .services import PaymentService

PAYMENT_SECRET = getattr(settings, 'PAYMENT_CALLBACK_SECRET', 'dev-secret')
NOWPAYMENTS_IPN_SECRET = getattr(settings, 'NOWPAYMENTS_IPN_SECRET', '')


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
            # Сохраняем order_id в сессию для анонимных пользователей
            request.session[f'order_{order.id}_owner'] = True
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


def _get_order_for_user(request, order_id):
    """Вернуть заказ если он принадлежит текущему пользователю или сессии."""
    if request.user.is_authenticated:
        return Order.objects.filter(id=order_id, user=request.user).first()
    # Для анонимов — проверяем сессию
    if request.session.get(f'order_{order_id}_owner'):
        return Order.objects.filter(id=order_id, user__isnull=True).first()
    return None


def payment_page(request, order_id):
    """Страница оплаты заказа."""
    order = _get_order_for_user(request, order_id)
    if order is None:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    
    # Проверяем, есть ли активный платёж
    payment = order.payments.filter(status=Payment.STATUS_PENDING).first()
    
    # Получаем redirect_url из сессии (если был перенаправлен)
    redirect_url = request.session.get(f'payment_redirect_{order_id}', '')
    
    return render(request, 'orders/payment.html', {
        'order': order,
        'payment': payment,
        'redirect_url': redirect_url,
    })


@ratelimit(key='ip', rate='5/m', block=True)
@require_POST
def payment_create(request, order_id):
    """Создание платежа, редирект на платёжный шлюз."""
    order = _get_order_for_user(request, order_id)
    if order is None:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()

    service = PaymentService()
    try:
        payment, redirect_url = service.create_payment(order)
    except ValidationError as e:
        messages.error(request, e.message)
        # Для AJAX-запросов возвращаем JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': e.message}, status=400)
        return redirect('orders:order_success', order_id=order_id)

    if redirect_url:
        request.session[f'payment_redirect_{order_id}'] = redirect_url
        return redirect('orders:payment_redirect', order_id=order_id)

    return redirect('orders:payment_page', order_id=order_id)


@require_GET
def payment_redirect(request, order_id):
    """Промежуточная страница — делает meta-refresh редирект на внешний шлюз."""
    redirect_url = request.session.get(f'payment_redirect_{order_id}', '')
    if not redirect_url:
        return redirect('orders:payment_page', order_id=order_id)
    return render(request, 'orders/payment_redirect.html', {'redirect_url': redirect_url})


@csrf_exempt
@ratelimit(key='ip', rate='10/m', block=True)
@require_POST
def payment_callback(request):
    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return HttpResponseBadRequest('Invalid JSON')

    # NowPayments передаёт подпись в заголовке x-nowpayments-sig
    signature = (
        request.headers.get('x-nowpayments-sig')
        or request.headers.get('X-Nowpayments-Sig')
        or request.headers.get('X-Payment-Signature', '')
    )
    service = PaymentService()
    # Для NowPayments используем IPN Secret; для Mock/прочих — PAYMENT_SECRET
    from .services import NowPaymentsGateway
    secret = NOWPAYMENTS_IPN_SECRET if isinstance(service.gateway, NowPaymentsGateway) else PAYMENT_SECRET
    try:
        service.handle_callback(data, signature, secret)
    except ValidationError as e:
        return HttpResponseBadRequest(str(e))

    return JsonResponse({'ok': True})


@require_GET
def payment_status(request, order_id):
    order = _get_order_for_user(request, order_id)
    if order is None:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    order.payments.prefetch_related('payments')

    payment = order.payments.first()
    return JsonResponse({
        'order_id': order.id,
        'order_status': order.status,
        'order_paid': order.paid,
        'payment_id': payment.payment_id if payment else None,
        'payment_status': payment.status if payment else None,
    })
