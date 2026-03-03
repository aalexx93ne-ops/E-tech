/**
 * Логика сравнения товаров
 * Обрабатывает выбор товаров, открытие модального окна и отображение сравнения
 */

(function() {
    'use strict';

    // Хранение выбранных товаров в sessionStorage
    const STORAGE_KEY = 'comparison_selected_products';

    // Получение выбранных товаров
    function getSelectedProducts() {
        try {
            const data = sessionStorage.getItem(STORAGE_KEY);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            console.error('Error reading selected products:', e);
            return [];
        }
    }

    // Сохранение выбранных товаров
    function saveSelectedProducts(products) {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(products));
        } catch (e) {
            console.error('Error saving selected products:', e);
        }
    }

    // Обновление состояния кнопок
    function updateCompareButtons() {
        const selectedProducts = getSelectedProducts();
        
        document.querySelectorAll('.compare-btn').forEach(btn => {
            const productId = parseInt(btn.dataset.productId, 10);
            
            if (selectedProducts.includes(productId)) {
                btn.classList.add('is-active');
            } else {
                btn.classList.remove('is-active');
            }
            
            // Блокируем кнопку, если уже выбрано 2 товара и этот не в выборе
            if (selectedProducts.length >= 2 && !selectedProducts.includes(productId)) {
                btn.disabled = true;
            } else {
                btn.disabled = false;
            }
        });

        // Обновление подсказки
        updateHint(selectedProducts);
    }

    // Обновление подсказки
    function updateHint(selectedProducts) {
        let hint = document.getElementById('comparisonHint');
        
        if (!hint) {
            hint = document.createElement('div');
            hint.id = 'comparisonHint';
            hint.className = 'comparison-hint';
            document.body.appendChild(hint);
        }

        if (selectedProducts.length === 1) {
            hint.textContent = 'Выберите ещё 1 товар для сравнения';
            hint.classList.add('is-visible');
        } else if (selectedProducts.length >= 2) {
            hint.textContent = 'Выбрано 2 товара. Нажмите на кнопку сравнения для просмотра.';
            hint.classList.add('is-visible');
        } else {
            hint.classList.remove('is-visible');
        }
    }

    // Добавление товара к сравнению
    function addToComparison(productId) {
        const selectedProducts = getSelectedProducts();
        
        if (selectedProducts.length >= 2) {
            alert('Можно сравнивать только 2 товара одновременно');
            return false;
        }

        if (selectedProducts.includes(productId)) {
            return removeFromComparison(productId);
        }

        selectedProducts.push(productId);
        saveSelectedProducts(selectedProducts);
        updateCompareButtons();

        // Если выбрано 2 товара — открываем модальное окно
        if (selectedProducts.length === 2) {
            openComparisonModal(selectedProducts);
        }

        return true;
    }

    // Удаление товара из сравнения
    function removeFromComparison(productId) {
        const selectedProducts = getSelectedProducts();
        const newProducts = selectedProducts.filter(id => id !== productId);
        saveSelectedProducts(newProducts);
        updateCompareButtons();
        return newProducts;
    }

    // Открытие модального окна сравнения
    function openComparisonModal(productIds) {
        const modal = document.getElementById('comparisonModal');
        const modalBody = document.getElementById('comparisonModalBody');
        
        if (!modal || !modalBody) {
            console.error('Modal elements not found');
            return;
        }

        // Показываем индикатор загрузки
        modalBody.innerHTML = '<div class="text-center py-4">Загрузка...</div>';
        modal.classList.add('is-visible');

        // Загружаем данные через API
        fetch(`/api/comparison/?product_ids=${productIds.join(',')}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    modalBody.innerHTML = `<div class="error-message">${data.error}</div>`;
                    return;
                }
                renderComparisonTable(data, modalBody);
            })
            .catch(error => {
                console.error('Error loading comparison data:', error);
                modalBody.innerHTML = '<div class="error-message">Ошибка загрузки данных</div>';
            });
    }

    // Отрисовка таблицы сравнения
    function renderComparisonTable(data, container) {
        const { products, metrics } = data;

        let html = `
            <div class="comparison-table-wrapper">
                <table class="comparison-table">
                    <thead>
                        <tr>
                            <th class="metric-name">Характеристика</th>
                            ${products.map(p => `
                                <th class="product-column">
                                    <div class="product-thumb">
                                        <img src="${p.image || '/static/img/placeholder.png'}" alt="${p.name}">
                                        <span class="product-name">${p.name}</span>
                                    </div>
                                </th>
                            `).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${metrics.map(metric => `
                            <tr class="metric-row">
                                <td class="metric-name">${metric.name}</td>
                                ${metric.products.map(p => `
                                    <td class="product-value ${p.is_best ? 'is-best' : ''} ${p.is_worst ? 'is-worst' : ''} ${p.is_tie ? 'is-tie' : ''}">
                                        ${p.raw_value}
                                    </td>
                                `).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            <div class="modal-actions">
                <button class="button" id="closeModal">Закрыть</button>
            </div>
        `;

        container.innerHTML = html;

        // Навешиваем обработчик на кнопку
        document.getElementById('closeModal').addEventListener('click', closeModal);
    }

    // Закрытие модального окна (сбрасывает выбор!)
    function closeModal() {
        const modal = document.getElementById('comparisonModal');
        if (modal) {
            modal.classList.remove('is-visible');
        }
        
        // Сбрасываем выбор товаров
        clearComparison();
    }

    // Очистка сравнения
    function clearComparison() {
        saveSelectedProducts([]);
        updateCompareButtons();
        closeModal();
    }

    // Инициализация
    function init() {
        // Навешиваем обработчики на кнопки сравнения
        document.querySelectorAll('.compare-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const productId = parseInt(this.dataset.productId, 10);
                addToComparison(productId);
            });
        });

        // Обработчик закрытия модального окна по клику вне его
        const modal = document.getElementById('comparisonModal');
        if (modal) {
            modal.addEventListener('click', function(e) {
                if (e.target === this) {
                    closeModal();
                }
            });
        }

        // Обработчик клавиши Escape
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeModal();
            }
        });
        
        // Обработчик на крестик в модальном окне
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', closeModal);
        });

        // Обновляем состояние кнопок при загрузке
        updateCompareButtons();
    }

    // Запуск после загрузки DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Делаем функции доступными глобально (для использования в HTML)
    window.comparison = {
        addToComparison,
        removeFromComparison,
        getSelectedProducts,
        clearComparison,
        closeModal
    };
})();
