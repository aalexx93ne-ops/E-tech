document.addEventListener('DOMContentLoaded', function() {
    const checkoutBtn = document.querySelector('.checkout');
    const modal = document.getElementById('empty-cart-modal');
    const closeBtn = document.getElementById('close-modal');
    const itemRows = document.querySelectorAll('.cart-table tbody tr:not(.total)');

    checkoutBtn.addEventListener('click', function(e) {
        if (itemRows.length === 0) {
            e.preventDefault();
            modal.classList.add('show');
        }
    });

    closeBtn.addEventListener('click', function() {
        modal.classList.remove('show');
    });

    // Закрытие модального окна при клике на оверлей
    modal.addEventListener('click', function(e) {
        if (e.target === modal.querySelector('.modal-overlay')) {
            modal.classList.remove('show');
        }
    });
});
