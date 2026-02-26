from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from orders.models import Order
from .forms import UserProfileForm

ORDERS_PER_PAGE = 10


@login_required
def profile_view(request):
    orders_qs = (Order.objects.filter(user=request.user)
                 .prefetch_related('items')
                 .order_by('-created'))
    paginator = Paginator(orders_qs, ORDERS_PER_PAGE)
    page = request.GET.get('page', 1)
    orders = paginator.get_page(page)
    return render(request, 'users/profile.html', {
        'orders': orders,
    })


@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'users/profile_edit.html', {'form': form})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        id=order_id, user=request.user,
    )
    return render(request, 'users/order_detail.html', {'order': order})
