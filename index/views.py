# index/views.py
from collections import defaultdict
from django.views.generic import ListView, DetailView, FormView
from django.views.generic.detail import SingleObjectMixin
from django.urls import reverse
from django.shortcuts import redirect
from django.db.models import Q, Avg
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
import logging
from .models import Product, Category, Brand, Tag, Banner, ProductSpecification, SpecificationType, Review
from cart.forms import CartAddProductForm
from .forms import ReviewForm

logger = logging.getLogger(__name__)
SIDEBAR_CACHE_TTL = 60 * 15  # 15 минут
MAX_PRICE_VALUE = 10_000_000  # Максимальная цена для защиты от DoS


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

        # Фильтр по цене с валидацией (защита от DoS)
        if price_from:
            try:
                price_val = float(self._clean_price(price_from))
                if price_val > MAX_PRICE_VALUE:
                    logger.warning(f"Попытка фильтрации с чрезмерной ценой: {price_from}")
                    price_val = MAX_PRICE_VALUE
                queryset = queryset.filter(price__gte=price_val)
            except (ValueError, TypeError) as e:
                logger.warning(f"Некорректное значение price_from: {price_from}, ошибка: {e}")
                pass
        if price_to:
            try:
                price_val = float(self._clean_price(price_to))
                if price_val > MAX_PRICE_VALUE:
                    logger.warning(f"Попытка фильтрации с чрезмерной ценой: {price_to}")
                    price_val = MAX_PRICE_VALUE
                queryset = queryset.filter(price__lte=price_val)
            except (ValueError, TypeError) as e:
                logger.warning(f"Некорректное значение price_to: {price_to}, ошибка: {e}")
                pass

        if category_slugs:
            queryset = queryset.filter(category__slug__in=category_slugs)
        if brand_slugs:
            queryset = queryset.filter(brand__slug__in=brand_slugs)
        if tag_slugs:
            queryset = queryset.filter(tags__slug__in=tag_slugs)
        if discount == '1':
            queryset = queryset.filter(discount__isnull=False)

        # Фильтр по характеристикам с валидацией spec_slug (защита от SQL-инъекции)
        spec_filters = {}
        valid_spec_slugs = set(
            SpecificationType.objects.values_list('slug', flat=True)
        )
        for key, values in self.request.GET.lists():
            if key.startswith('spec_'):
                spec_slug = key.replace('spec_', '', 1)  # Удаляем только первый 'spec_'
                # Валидация: slug должен существовать в БД и быть безопасным
                if spec_slug in valid_spec_slugs and spec_slug.replace('-', '').replace('_', '').isalnum():
                    spec_filters[spec_slug] = values
                else:
                    logger.warning(f"Попытка инъекции через spec_slug: {spec_slug}")

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


class ProductDisplay(DetailView):
    model = Product
    template_name = 'index/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.select_related(
            'category', 'brand', 'discount', 'stock'
        ).prefetch_related(
            'images', 
            'specifications__spec_type',
            'reviews__user'
        ).annotate(
            avg_rating=Avg('reviews__rating')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart_product_form'] = CartAddProductForm()
        context['review_form'] = ReviewForm()
        context['reviews'] = self.object.reviews.all()
        return context


class ReviewFormView(SingleObjectMixin, FormView):
    template_name = 'index/product_detail.html'
    form_class = ReviewForm
    model = Product

    @method_decorator(ratelimit(key='user_or_ip', rate='5/m', block=True))
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account_login')
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        review = form.save(commit=False)
        review.product = self.object
        review.user = self.request.user
        review.name = self.request.user.get_full_name() or self.request.user.username
        review.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('index:product_detail', kwargs={'slug': self.object.slug})


class ProductDetailView(DetailView):
    def get(self, request, *args, **kwargs):
        view = ProductDisplay.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = ReviewFormView.as_view()
        return view(request, *args, **kwargs)


class ProductSearchView(ProductListView):
    template_name = 'index/search.html'
    htmx_partial_template = 'index/partials/search_content.html'

    @method_decorator(ratelimit(key='ip', rate='10/m', block=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

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
