from django.contrib import admin
from django.db.models import Sum
from .models import DBCart, DBCartItem


class DBCartItemInline(admin.TabularInline):
    model = DBCartItem
    extra = 0
    readonly_fields = ('added_at',)


@admin.register(DBCart)
class DBCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'items_count', 'updated_at')
    list_select_related = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [DBCartItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _items_count=Sum('items__quantity'),
        )

    def items_count(self, obj):
        return obj._items_count or 0
    items_count.short_description = 'Товаров'
    items_count.admin_order_field = '_items_count'
