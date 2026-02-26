from decimal import Decimal
from django.contrib.auth import get_user_model
from index.models import Product, Category, Brand, Stock
from orders.models import Order, OrderItem, Payment

User = get_user_model()


def make_user(username='buyer', email='buyer@test.com', password='pass123'):
    return User.objects.create_user(username=username, email=email, password=password)


_product_counter = [0]

def make_product(name='Товар', slug=None, price='5000.00', stock_qty=10):
    _product_counter[0] += 1
    if slug is None:
        slug = f'tovar-{_product_counter[0]}'
    cat, _ = Category.objects.get_or_create(name='Тест', slug='test')
    brand, _ = Brand.objects.get_or_create(name='BrandX', slug='brandx')
    p = Product.objects.create(
        name=name, slug=slug,
        price=Decimal(price),
        category=cat, brand=brand,
    )
    Stock.objects.create(product=p, quantity=stock_qty)
    return p


def make_order(user=None, paid=False):
    return Order.objects.create(
        user=user,
        first_name='Иван', last_name='Иванов',
        email='ivan@example.com',
        address='ул. Ленина, 1', city='Москва',
        paid=paid,
    )


def make_order_with_items(user=None, price='5000.00', quantity=2):
    product = make_product(price=price)
    order = make_order(user=user)
    OrderItem.objects.create(
        order=order, product=product,
        price=Decimal(price), quantity=quantity,
    )
    return order


def make_payment(order, status=Payment.STATUS_PENDING, payment_id=None):
    import uuid
    return Payment.objects.create(
        order=order,
        payment_id=payment_id or f'pay_{uuid.uuid4().hex[:12]}',
        amount=order.get_total_cost(),
        status=status,
    )
