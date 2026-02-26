from django import template
from orders.models import Order

register = template.Library()

STATUS_CSS = {
    Order.STATUS_NEW: 'status-new',
    Order.STATUS_CONFIRMED: 'status-confirmed',
    Order.STATUS_SHIPPED: 'status-shipped',
    Order.STATUS_DELIVERED: 'status-delivered',
    Order.STATUS_CANCELLED: 'status-cancelled',
}

@register.inclusion_tag('orders/partials/status_badge.html')
def status_badge(order):
    return {
        'label': order.get_status_display(),
        'css_class': STATUS_CSS.get(order.status, ''),
    }
