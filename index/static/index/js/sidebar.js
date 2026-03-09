function toggleList(listId, btn) {
  var list = document.getElementById(listId);
  if (!list) return;
  var isExpanded = btn.classList.contains('expanded');

  list.classList.toggle('show-all');
  if (isExpanded) {
    btn.textContent = btn.textContent.replace('Скрыть', 'Показать все');
    btn.classList.remove('expanded');
  } else {
    btn.textContent = btn.textContent.replace('Показать все', 'Скрыть');
    btn.classList.add('expanded');
  }
}

/* ─── Привязка кнопок «Показать все» через data-атрибуты (CSP-совместимо) ─── */

document.addEventListener('DOMContentLoaded', function () {
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-toggle-list]');
    if (btn) {
      toggleList(btn.getAttribute('data-toggle-list'), btn);
    }
  });

  /* ─── Фильтр цены: форматирование и очистка ─── */

  var priceInputs = document.querySelectorAll('.price-filter input[type="text"]');

  priceInputs.forEach(function (input) {
    input.addEventListener('input', function () {
      var pos = this.selectionStart;
      var before = this.value.length;
      this.value = formatPrice(this.value);
      var after = this.value.length;
      this.setSelectionRange(pos + (after - before), pos + (after - before));
    });
  });

  var sidebar = document.querySelector('.sidebar');
  if (sidebar) {
    sidebar.addEventListener('submit', function () {
      priceInputs.forEach(function (input) {
        input.value = cleanPriceValue(input.value);
      });
    });
  }
});

/* ─── Фильтр цены: утилиты ─── */

function cleanPriceValue(str) {
  var cleaned = str.replace(/[^\d.,]/g, '');
  cleaned = cleaned.replace(/[.,](\d{3})(?!\d)/g, '$1');
  cleaned = cleaned.replace(',', '.');
  var parts = cleaned.split('.');
  if (parts.length > 2) {
    cleaned = parts[0] + '.' + parts.slice(1).join('');
  }
  return cleaned;
}

function formatPrice(value) {
  if (!value) return '';
  var num = cleanPriceValue(value);
  var parts = num.split('.');
  var intPart = parts[0];
  var decPart = parts[1];
  var formatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return decPart !== undefined ? formatted + '.' + decPart : formatted;
}
