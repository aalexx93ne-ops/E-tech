# index/views.py
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import Product, Category, Brand, Tag, Banner, SpecificationType, ProductSpecification
from cart.forms import CartAddProductForm


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
        context['categories'] = Category.objects.all()
        context['brands'] = Brand.objects.all()
        context['tags'] = Tag.objects.all()
        context['banners'] = Banner.objects.filter(is_active=True)

        context['selected_categories'] = self.request.GET.getlist('category')
        context['selected_brands'] = self.request.GET.getlist('brand')
        context['selected_tags'] = self.request.GET.getlist('tag')
        context['discount_only'] = self.request.GET.get('discount') == '1'
        context['price_from'] = self.request.GET.get('price_from')
        context['price_to'] = self.request.GET.get('price_to')

        # Фильтры по характеристикам для сайдбара
        context['spec_filters'] = self.get_spec_filters()

        return context

    def get_spec_filters(self):
        """Получает уникальные значения для каждого типа характеристик"""
        spec_types = SpecificationType.objects.all()
        spec_filters = []

        for spec_type in spec_types:
            # Получаем все уникальные значения для этого типа характеристики
            values = ProductSpecification.objects.filter(
                spec_type=spec_type
            ).values_list('value', flat=True).distinct().order_by('value')

            if values:
                selected_values = self.request.GET.getlist(f'spec_{spec_type.slug}')
                spec_filters.append({
                    'name': spec_type.name,
                    'slug': spec_type.slug,
                    'values': list(values),
                    'selected_values': selected_values
                })

        return spec_filters


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
