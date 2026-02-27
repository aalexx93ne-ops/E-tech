from django.contrib import admin
from .models import Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email',
                    'city', 'status', 'paid', 'created']
    list_filter = ['status', 'paid', 'created']
    list_editable = ['status', 'paid']
    search_fields = ['first_name', 'last_name', 'email']
    inlines = [OrderItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'payment_id', 'amount', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['payment_id', 'order__id']
    readonly_fields = ['payment_id', 'amount', 'created_at', 'updated_at']
