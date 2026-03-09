from django.urls import path
from .views import ProductListView, ProductDetailView, ProductSearchView, ComparisonView, ComparisonAPIView

app_name = 'index'

urlpatterns = [
    # Главная страница с каталогом
    path('', ProductListView.as_view(), name='index'),

    # Страница конкретного товара
    path('product/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),

    # Поиск
    path('search/', ProductSearchView.as_view(), name='search'),

    # Сравнение товаров
    path('comparison/', ComparisonView.as_view(), name='comparison'),
]

# API URLs
urlpatterns += [
    path('api/comparison/', ComparisonAPIView.as_view(), name='api_comparison'),
]
