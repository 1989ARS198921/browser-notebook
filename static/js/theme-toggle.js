// static/js/theme-toggle.js
// -*- coding: utf-8 -*-

// --- НОВОЕ: Глобальная функция для переключения темы ---
function toggleTheme() {
    // Получаем текущую тему из атрибута data-theme
    let currentTheme = document.documentElement.getAttribute('data-theme');
    // Определяем новую тему
    let newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    // Устанавливаем новую тему на элемент <html>
    document.documentElement.setAttribute('data-theme', newTheme);

    // Сохраняем выбранную тему в localStorage
    localStorage.setItem('theme', newTheme);

    // Обновляем иконку на странице (если нужно, но обычно это делается в CSS)
    // updateButtonIcon(newTheme); // Убираем, так как кнопка уже в шаблоне
}
// --- /НОВОЕ ---

// --- НОВОЕ: Загрузка сохранённой темы при загрузке страницы ---
document.addEventListener('DOMContentLoaded', function () {
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

    // Определяем начальную тему
    let initialTheme = 'light';
    if (savedTheme) {
        // Если тема была сохранена пользователем, используем её
        initialTheme = savedTheme;
    } else if (systemPrefersDark) {
        // Иначе, если системная тема тёмная, используем её
        initialTheme = 'dark';
    }

    // Устанавливаем тему на элемент <html>
    document.documentElement.setAttribute('data-theme', initialTheme);

    // Обновляем иконку кнопки (если нужно, в зависимости от начальной темы)
    // Это может быть сделано в CSS через [data-theme="dark"] .theme-toggle-btn::after { content: '☀️'; }
    // или в JS, если нужно динамически
    updateThemeButtonIcon(initialTheme);
});

function updateThemeButtonIcon(theme) {
    const button = document.querySelector('.theme-toggle-btn');
    if (button) {
        if (theme === 'dark') {
            button.innerHTML = '☀️'; // Иконка светлой темы
        } else {
            button.innerHTML = '🌙'; // Иконка тёмной темы
        }
    }
}
// --- /НОВОЕ ---

// --- НОВОЕ: Обновление темы при изменении системной (если пользователь не выбрал тему вручную) ---
// Это нужно выполнить только один раз при загрузке страницы
document.addEventListener('DOMContentLoaded', function () {
    const savedTheme = localStorage.getItem('theme');
    if (!savedTheme) {
        // Если пользователь не выбрал тему вручную, слушаем системную
        window.matchMedia('(prefers-color-scheme: dark)')
            .addEventListener('change', function(e) {
                const newTheme = e.matches ? 'dark' : 'light';
                document.documentElement.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme); // Сохраняем системную тему, если пользователь не менял вручную
                updateThemeButtonIcon(newTheme);
            });
    }
});
// --- /НОВОЕ ---