document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.order-form');
    const modal = document.getElementById('empty-cart-modal');
    const itemRows = document.querySelectorAll('.cart-table tbody tr:not(.total)');

    if (form && modal) {
        form.addEventListener('submit', function(e) {
            if (itemRows.length === 0) {
                e.preventDefault();
                modal.classList.add('show');
            }
        });

        const closeBtn = document.getElementById('close-modal');

        closeBtn.addEventListener('click', function() {
            modal.classList.remove('show');
        });

        // Закрытие модального окна при клике на оверлей
        modal.addEventListener('click', function(e) {
            if (e.target === modal.querySelector('.modal-overlay')) {
                modal.classList.remove('show');
            }
        });
    }
});
