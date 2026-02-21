from django.contrib import admin
from .models import DBCart, DBCartItem


class DBCartItemInline(admin.TabularInline):
    model = DBCartItem
    extra = 0
    readonly_fields = ('added_at',)


@admin.register(DBCart)
class DBCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'items_count', 'total_price', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [DBCartItemInline]

    def items_count(self, obj):
        return len(obj)
    items_count.short_description = 'Товаров'

    def total_price(self, obj):
        return obj.get_total_price()
    total_price.short_description = 'Сумма'
