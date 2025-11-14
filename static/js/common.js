/**
 * Общие утилиты для всех страниц приложения
 */

// Экранирование HTML для безопасности
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Форматирование валюты
function formatCurrency(amount) {
    return new Intl.NumberFormat('ru-RU').format(amount);
}

