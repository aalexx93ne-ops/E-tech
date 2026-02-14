from django.contrib import admin
from .models import Category, Brand, Discount, Product, ProductImage, Review, Stock, SpecificationType, ProductSpecification


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'percent', 'start_date', 'end_date', 'is_active')
    readonly_fields = ('is_active',)


class StockInline(admin.TabularInline):
    model = Stock
    extra = 0
    fields = ['quantity', 'is_available']
    readonly_fields = []
    can_delete = False


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 1
    autocomplete_fields = ['spec_type']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'price',
                    'get_final_price', 'discount', 'stock_quantity')
    list_editable = ('price',)
    list_filter = ('category', 'brand', 'discount')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [StockInline, ProductSpecificationInline]

    def stock_quantity(self, obj):
        return obj.stock.quantity if hasattr(obj, 'stock') else 0
    stock_quantity.short_description = 'Количество на складе'


@admin.register(SpecificationType)
class SpecificationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ('product', 'spec_type', 'value')
    list_filter = ('spec_type',)
    search_fields = ('product__name', 'spec_type__name', 'value')
    autocomplete_fields = ['product', 'spec_type']


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'alt_text')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'rating', 'created_at')
    list_filter = ('rating',)


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'is_available')
    list_editable = ('quantity', 'is_available')
    list_display_links = ('product',)
