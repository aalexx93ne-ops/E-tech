from django.contrib import admin
from django.db import models
from django.forms import ImageField
from .models import (
    Category, Brand, Discount, Product, ProductImage, Review, Stock,
    SpecificationType, ProductSpecification, Banner,
)
from appx.validators import product_image_validator, banner_image_validator


# Валидация изображений в админке через formfield_overrides
# Используем функции-валидаторы вместо классов для совместимости с миграциями


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
    list_select_related = ('category', 'brand', 'discount', 'stock')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [StockInline, ProductSpecificationInline]

    def stock_quantity(self, obj):
        try:
            return obj.stock.quantity
        except Stock.DoesNotExist:
            return 0
    stock_quantity.short_description = 'Количество на складе'


@admin.register(SpecificationType)
class SpecificationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ('product', 'spec_type', 'value')
    list_select_related = ('product', 'spec_type')
    list_filter = ('spec_type',)
    search_fields = ('product__name', 'spec_type__name', 'value')
    autocomplete_fields = ['product', 'spec_type']


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'alt_text')
    list_select_related = ('product',)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'image':
            from django.forms import ImageField
            field = super().formfield_for_dbfield(db_field, request, **kwargs)
            field = ImageField(validators=product_image_validator)
            return field
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('alt_text', 'is_active')
    list_filter = ('is_active',)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'image':
            from django.forms import ImageField
            field = super().formfield_for_dbfield(db_field, request, **kwargs)
            field = ImageField(validators=banner_image_validator)
            return field
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'rating', 'created_at')
    list_select_related = ('product',)
    list_filter = ('rating',)


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'is_available')
    list_select_related = ('product',)
    list_editable = ('quantity', 'is_available')
    list_display_links = ('product',)
