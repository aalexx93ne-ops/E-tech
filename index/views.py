# index/views.py
from collections import defaultdict
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.core.cache import cache
from .models import Product, Category, Brand, Tag, Banner, SpecificationType, ProductSpecification
from cart.forms import CartAddProductForm

SIDEBAR_CACHE_TTL = 60 * 15  # 15 минут


class ProductListView(ListView):
    model = Product
    template_name = 'index/index.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.select_related(
            'category', 'brand', 'discount', 'stock').prefetch_related('images', 'tags', 'specifications__spec_type')

        category_slugs = self.request.GET.getlist('category')
        brand_slugs = self.request.GET.getlist('brand')
        tag_slugs = self.request.GET.getlist('tag')
        discount = self.request.GET.get('discount')
        price_from = self.request.GET.get('price_from')
        price_to = self.request.GET.get('price_to')

        # Фильтр по цене
        if price_from:
            try:
                queryset = queryset.filter(price__gte=float(price_from))
            except ValueError:
                pass
        if price_to:
            try:
                queryset = queryset.filter(price__lte=float(price_to))
            except ValueError:
                pass

        if category_slugs:
            queryset = queryset.filter(category__slug__in=category_slugs)
        if brand_slugs:
            queryset = queryset.filter(brand__slug__in=brand_slugs)
        if tag_slugs:
            queryset = queryset.filter(tags__slug__in=tag_slugs)
        if discount == '1':
            queryset = queryset.filter(discount__isnull=False)

        # Фильтр по характеристикам
        spec_filters = {}
        for key, values in self.request.GET.lists():
            if key.startswith('spec_'):
                spec_slug = key.replace('spec_', '')
                spec_filters[spec_slug] = values

        if spec_filters:
            for spec_slug, values in spec_filters.items():
                queryset = queryset.filter(
                    specifications__spec_type__slug=spec_slug,
                    specifications__value__in=values
                )

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Кэшируем данные сайдбара — они меняются редко
        sidebar = cache.get('sidebar_data')
        if sidebar is None:
            sidebar = {
                'categories': list(Category.objects.all()),
                'brands': list(Brand.objects.all()),
                'tags': list(Tag.objects.all()),
                'banners': list(Banner.objects.filter(is_active=True)),
                'spec_filters': self.get_spec_filters(),
            }
            cache.set('sidebar_data', sidebar, SIDEBAR_CACHE_TTL)

        context.update(sidebar)

        # selected_values зависят от GET — проставляем после кэша
        for sf in context.get('spec_filters', []):
            sf['selected_values'] = self.request.GET.getlist(f'spec_{sf["slug"]}')

        context['selected_categories'] = self.request.GET.getlist('category')
        context['selected_brands'] = self.request.GET.getlist('brand')
        context['selected_tags'] = self.request.GET.getlist('tag')
        context['discount_only'] = self.request.GET.get('discount') == '1'
        context['price_from'] = self.request.GET.get('price_from')
        context['price_to'] = self.request.GET.get('price_to')

        return context

    def get_spec_filters(self):
        """Получает уникальные значения для каждого типа характеристик — 1 запрос"""
        rows = (
            ProductSpecification.objects
            .select_related('spec_type')
            .values_list('spec_type__slug', 'spec_type__name', 'value')
            .distinct()
            .order_by('spec_type__name', 'value')
        )

        grouped = defaultdict(lambda: {'values': []})
        for slug, name, value in rows:
            grouped[slug]['name'] = name
            grouped[slug]['slug'] = slug
            grouped[slug]['values'].append(value)

        return list(grouped.values())


class ProductDetailView(DetailView):
    model = Product
    template_name = 'index/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart_product_form'] = CartAddProductForm()
        return context


class ProductSearchView(ProductListView):
    """
    Представление для поиска товаров.
    Наследуется от ProductListView, чтобы сохранить пагинацию и контекст (фильтры и т.д.).
    """
    def get_queryset(self):
        # Начинаем с базового queryset (с select_related/prefetch_related)
        queryset = Product.objects.select_related(
            'category', 'brand', 'discount', 'stock').prefetch_related('images', 'tags')
        
        query = self.request.GET.get('q')
        
        if query:
            # Фильтруем по названию или описанию (регистронезависимо)
            queryset = queryset.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query)
            )
        else:
            # Если запрос пустой, можно вернуть пустой список или все товары
            # Лучше вернуть пустой список или сообщение, но пока вернем все
            pass
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем поисковый запрос в контекст, чтобы отобразить его в шаблоне
        context['query'] = self.request.GET.get('q')
        # Убираем баннеры на странице поиска, чтобы не отвлекать
        context['banners'] = None
        return context
