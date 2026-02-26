from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def merge_cart_on_login(sender, request, user, **kwargs):
    from .cart import Cart
    if not hasattr(request, 'user'):
        request.user = user
    cart = Cart(request)
    cart.merge_session_cart()
