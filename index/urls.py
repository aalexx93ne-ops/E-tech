from django.urls import path
from .views import ProductListView, ProductDetailView, ProductSearchView

app_name = 'index'

urlpatterns = [
    # Главная страница с каталогом
    path('', ProductListView.as_view(), name='index'),

    # Страница конкретного товара
    path('product/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),

    # Поиск
    path('search/', ProductSearchView.as_view(), name='search'),
]
