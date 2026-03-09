# Дизайн: Система сравнения товаров

**Дата:** 2026-03-03
**Источник:** comparison.md (ТЗ)

## Отличия от ТЗ

- Убран тип сравнения `formula` (безопасность eval) — остаются `higher_better`, `lower_better`, `categorical`, `boolean`
- Убраны поля `formula` и `field_name` из `ComparisonMetric`
- Убрана data migration для метрик с типом `formula` (screen_resolution, resolution)
- Убран Admin API (POST `/api/comparison/metrics/`) — метрики управляются через Django admin
- Всё остальное — строго по ТЗ

## Архитектура

Всё размещается в приложении `index`. Новые модели: `ComparisonMetric`, `ProductCharacteristic`.

### Модели
- `ComparisonMetric` — конфигурация метрик по категориям (без formula/field_name)
- `ProductCharacteristic` — значения характеристик товаров (value_numeric, value_text, value_boolean, raw_value)

### Backend
- `index/services.py` — `ComparisonService` с логикой сравнения 4 типов
- `index/views.py` — `comparison_api` (GET, JSON), `comparison_view` (страница)
- `index/urls.py` — `/comparison/`, `/api/comparison/`

### Frontend
- Кнопка "Сравнить" в `product_card.html`
- Модальное окно `comparison_modal.html` (include в base.html)
- JS: `static/index/js/comparison.js` — выбор товаров, fetch API, рендер таблицы
- CSS: `static/index/css/comparison.css`
- Хранение выбора в JS переменной (сбрасывается при уходе со страницы)

### Admin
- `ComparisonMetricAdmin` — с фильтрами по категории
- `ProductCharacteristicAdmin` — с фильтрами по товару и метрике
