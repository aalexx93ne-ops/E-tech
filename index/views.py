# index/views.py
from collections import defaultdict
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.core.cache import cache
from .models import Product, Category, Brand, Tag, Banner, ProductSpecification
from cart.forms import CartAddProductForm

SIDEBAR_CACHE_TTL = 60 * 15  # 15 минут


class ProductListView(ListView):
    model = Product
    template_name = 'index/index.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.select_related(
            'category', 'brand', 'discount')

        category_slugs = self.request.GET.getlist('category')
        brand_slugs = self.request.GET.getlist('brand')
        tag_slugs = self.request.GET.getlist('tag')
        discount = self.request.GET.get('discount')
        price_from = self.request.GET.get('price_from')
        price_to = self.request.GET.get('price_to')

        # Фильтр по цене
        if price_from:
            try:
                queryset = queryset.filter(price__gte=float(self._clean_price(price_from)))
            except (ValueError, TypeError):
                pass
        if price_to:
            try:
                queryset = queryset.filter(price__lte=float(self._clean_price(price_to)))
            except (ValueError, TypeError):
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

        queryset = queryset.distinct()

        sort = self.request.GET.get('sort', '')
        sort_map = {
            'price_asc':  'price',
            'price_desc': '-price',
            'new':        '-id',
        }
        if sort in sort_map:
            queryset = queryset.order_by(sort_map[sort])

        return queryset

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if request.headers.get('HX-Request'):
            from django.template.response import TemplateResponse
            partial = getattr(self, 'htmx_partial_template', 'index/partials/product_list.html')
            return TemplateResponse(request, partial, response.context_data)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_string'] = params.urlencode()

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

        # selected_values зависят от GET — копируем список чтобы не мутировать кэш
        context['spec_filters'] = [
            {**sf, 'selected_values': self.request.GET.getlist(f'spec_{sf["slug"]}')}
            for sf in context.get('spec_filters', [])
        ]

        context['selected_categories'] = self.request.GET.getlist('category')
        context['selected_brands'] = self.request.GET.getlist('brand')
        context['selected_tags'] = self.request.GET.getlist('tag')
        context['discount_only'] = self.request.GET.get('discount') == '1'
        context['price_from'] = self.request.GET.get('price_from')
        context['price_to'] = self.request.GET.get('price_to')
        context['current_sort'] = self.request.GET.get('sort', '')

        return context

    @staticmethod
    def _clean_price(value):
        """
        Очищает ввод цены: '35 000,50' → '35000.50', '40.000' → '40000'.
        Точка/запятая + ровно 3 цифры в конце = разделитель тысяч.
        """
        import re
        value = value.replace(' ', '')
        # 40.000 или 35,000 → разделитель тысяч, убираем
        value = re.sub(r'[.,](\d{3})(?!\d)', r'\1', value)
        # Оставшаяся запятая — десятичный разделитель
        return value.replace(',', '.')

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

    def get_queryset(self):
        return Product.objects.select_related(
            'category', 'brand', 'discount', 'stock'
        ).prefetch_related('images', 'specifications__spec_type')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart_product_form'] = CartAddProductForm()
        return context


class ProductSearchView(ProductListView):
    template_name = 'index/search.html'
    htmx_partial_template = 'index/partials/search_content.html'

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
            # Если запрос пустой — возвращаем пустой queryset
            queryset = Product.objects.none()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем поисковый запрос в контекст, чтобы отобразить его в шаблоне
        context['query'] = self.request.GET.get('q')
        return context
