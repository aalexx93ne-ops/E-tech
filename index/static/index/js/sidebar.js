function toggleList(listId, btn) {
  const list = document.getElementById(listId);
  const hiddenItems = list.querySelectorAll('.hidden-item');
  const isExpanded = btn.classList.contains('expanded');

  if (isExpanded) {
    hiddenItems.forEach(item => item.style.display = 'none');
    btn.textContent = btn.textContent.replace('Скрыть', 'Показать все');
    btn.classList.remove('expanded');
  } else {
    hiddenItems.forEach(item => item.style.display = 'list-item');
    btn.textContent = btn.textContent.replace('Показать все', 'Скрыть');
    btn.classList.add('expanded');
  }
}

/* ─── Фильтр цены: форматирование и очистка ─── */

function cleanPriceValue(str) {
  // Убираем всё кроме цифр, точки и запятой
  let cleaned = str.replace(/[^\d.,]/g, '');
  // Точка/запятая + ровно 3 цифры в конце = разделитель тысяч, просто убираем
  // 40.000 → 40000, 35,000 → 35000
  // Но 40.00 → 40.00 (копейки), 40.5 → 40.5 (копейки)
  cleaned = cleaned.replace(/[.,](\d{3})(?!\d)/g, '$1');
  // Оставшиеся запятые — десятичный разделитель
  cleaned = cleaned.replace(',', '.');
  // Убираем лишние точки — оставляем только первую
  const parts = cleaned.split('.');
  if (parts.length > 2) {
    cleaned = parts[0] + '.' + parts.slice(1).join('');
  }
  return cleaned;
}

function formatPrice(value) {
  if (!value) return '';
  const num = cleanPriceValue(value);
  const [intPart, decPart] = num.split('.');
  // Добавляем пробелы как разделитель тысяч
  const formatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return decPart !== undefined ? formatted + '.' + decPart : formatted;
}

document.addEventListener('DOMContentLoaded', function () {
  const priceInputs = document.querySelectorAll('.price-filter input[type="text"]');

  priceInputs.forEach(function (input) {
    // Форматируем при вводе
    input.addEventListener('input', function () {
      const pos = this.selectionStart;
      const before = this.value.length;
      this.value = formatPrice(this.value);
      const after = this.value.length;
      // Корректируем позицию курсора
      this.setSelectionRange(pos + (after - before), pos + (after - before));
    });
  });

  // При отправке формы — очищаем значения до чистых чисел
  const sidebar = document.querySelector('.sidebar');
  if (sidebar) {
    sidebar.addEventListener('submit', function () {
      priceInputs.forEach(function (input) {
        input.value = cleanPriceValue(input.value);
      });
    });
  }
});
