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
