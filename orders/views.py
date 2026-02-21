from django.shortcuts import render, redirect
from cart.cart import Cart
from .forms import OrderCreateForm
from .models import Order, OrderItem

def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            if len(cart) == 0:
                return render(request, 'orders/create.html', {
                    'cart': cart, 'cart_items': [], 'cart_total_price': 0,
                    'form': form, 'show_modal': True,
                })
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
                for item in cart
            ])
            cart.clear()
            return render(request, 'orders/created.html', {'order': order})
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
