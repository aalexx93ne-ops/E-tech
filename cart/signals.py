import logging

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def merge_cart_on_login(sender, request, user, **kwargs):
    if not hasattr(request, 'session'):
        return
    from .cart import Cart
    if not hasattr(request, 'user'):
        request.user = user
    try:
        cart = Cart(request)
        cart.merge_session_cart()
    except Exception:
        logger.exception('Failed to merge session cart on login for user %s', user.pk)
