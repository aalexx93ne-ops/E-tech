from decimal import Decimal
from django.conf import settings
from django.db.models import Sum
from index.models import Product


class Cart:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        self.user = request.user if request.user.is_authenticated else None

        # Сессионная корзина — для анонимов и для мержа при логине
        self.cart = self.session.get(settings.CART_SESSION_ID, {})

        self._db_cart_cached = None
        self._db_cart_loaded = False

    @property
    def db_cart(self):
        """Ленивая загрузка БД-корзины — запрос только при реальном обращении."""
        if not self._db_cart_loaded:
            if self.user:
                from .models import DBCart
                self._db_cart_cached, _ = DBCart.objects.get_or_create(user=self.user)
            self._db_cart_loaded = True
        return self._db_cart_cached

    def add(self, product, quantity=1, update_quantity=False):
        if self.db_cart is not None:
            from .models import DBCartItem
            item, created = DBCartItem.objects.get_or_create(
                cart=self.db_cart,
                product=product,
                defaults={'quantity': quantity},
            )
            if not created:
                if update_quantity:
                    item.quantity = quantity
                else:
                    item.quantity += quantity
                item.save()
            self.db_cart.save()  # обновляем updated_at
        else:
            product_id = str(product.id)
            if product_id not in self.cart:
                self.cart[product_id] = {'quantity': 0,
                                         'price': str(product.get_final_price())}
            self.cart[product_id]['price'] = str(product.get_final_price())
            if update_quantity:
                self.cart[product_id]['quantity'] = quantity
            else:
                self.cart[product_id]['quantity'] += quantity
            self.save()

    def remove(self, product):
        if self.db_cart is not None:
            from .models import DBCartItem
            DBCartItem.objects.filter(
                cart=self.db_cart, product=product
            ).delete()
            self.db_cart.save()
        else:
            product_id = str(product.id)
            if product_id in self.cart:
                del self.cart[product_id]
                self.save()

    def __iter__(self):
        if self.db_cart is not None:
            from .models import DBCartItem
            items = (
                DBCartItem.objects
                .filter(cart=self.db_cart)
                .select_related('product', 'product__discount')
            )
            for item in items:
                yield {
                    'product': item.product,
                    'price': item.product.get_final_price(),
                    'quantity': item.quantity,
                    'total_price': item.get_total_price(),
                }
        else:
            product_ids = self.cart.keys()
            products = Product.objects.filter(id__in=product_ids)
            cart = self.cart.copy()
            for product in products:
                cart[str(product.id)]['product'] = product
            for item in cart.values():
                item['price'] = Decimal(item['price'])
                item['total_price'] = item['price'] * item['quantity']
                yield item

    def __len__(self):
        if self.user:
            from .models import DBCartItem
            result = DBCartItem.objects.filter(
                cart__user=self.user
            ).aggregate(total=Sum('quantity'))
            return result['total'] or 0
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        if self.db_cart is not None:
            return sum(
                item.product.get_final_price() * item.quantity
                for item in self.db_cart.items.select_related(
                    'product', 'product__discount'
                )
            )
        return sum(
            Decimal(item['price']) * item['quantity']
            for item in self.cart.values()
        )

    def clear(self):
        if self.db_cart is not None:
            self.db_cart.items.all().delete()
            self.db_cart.save()
        else:
            self.session.pop(settings.CART_SESSION_ID, None)
            self.cart = {}
            self.session.modified = True

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True

    def merge_session_cart(self):
        """Переносит товары из сессионной корзины в БД-корзину при логине."""
        session_cart = self.session.get(settings.CART_SESSION_ID)
        if not session_cart or self.db_cart is None:
            return

        from .models import DBCartItem
        product_ids = [int(pid) for pid in session_cart.keys()]
        products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}

        for pid_str, data in session_cart.items():
            pid = int(pid_str)
            product = products.get(pid)
            if not product:
                continue
            item, created = DBCartItem.objects.get_or_create(
                cart=self.db_cart,
                product=product,
                defaults={'quantity': data['quantity']},
            )
            if not created:
                item.quantity += data['quantity']
                item.save()

        del self.session[settings.CART_SESSION_ID]
        self.session.modified = True
        self.db_cart.save()
