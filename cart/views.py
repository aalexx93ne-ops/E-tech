from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from index.models import Product
from .cart import Cart


def _cart_body_context(cart):
    items = []
    total_price = 0
    for item in cart:
        total_price += item['total_price']
        items.append(item)
    return {
        'cart_items': items,
        'cart_total_price': total_price,
        'quantity_range': range(1, 21),
    }


def _htmx_cart_response(request, ctx):
    response = render(request, 'cart/partials/cart_content.html', ctx)
    response['HX-Trigger'] = 'cartUpdated'
    return response


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    update = request.POST.get('update') in ('true', 'True', '1')
    cart.add(product=product, quantity=quantity, update_quantity=update)

    if request.headers.get('HX-Request'):
        if request.headers.get('HX-Target') == 'cart-content':
            return _htmx_cart_response(request, _cart_body_context(cart))
        from django.http import HttpResponse
        response = HttpResponse(status=204)
        response['HX-Trigger'] = 'cartUpdated'
        return response

    return redirect('cart:cart_detail')


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)

    if request.headers.get('HX-Request'):
        return _htmx_cart_response(request, _cart_body_context(cart))

    return redirect('cart:cart_detail')


@require_POST
def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    if request.headers.get('HX-Request'):
        return _htmx_cart_response(request, _cart_body_context(cart))
    return redirect('cart:cart_detail')


def cart_counter(request):
    cart = Cart(request)
    return render(request, 'cart/partials/cart_counter.html', {'cart_count': len(cart)})


def cart_detail(request):
    cart = Cart(request)
    ctx = _cart_body_context(cart)
    return render(request, 'cart/detail.html', ctx)
