// static/js/theme-toggle.js
// -*- coding: utf-8 -*-

document.addEventListener('DOMContentLoaded', function () {
    const toggleButton = document.createElement('button');
    toggleButton.classList.add('theme-toggle-btn');
    toggleButton.type = 'button';
    toggleButton.ariaLabel = 'Переключить тему';

    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

    // Определяем начальную тему
    let initialTheme = 'light';
    if (savedTheme) {
        initialTheme = savedTheme;
    } else if (systemPrefersDark) {
        initialTheme = 'dark';
    }

    // Устанавливаем тему и иконку
    document.documentElement.setAttribute('data-theme', initialTheme);
    updateButtonIcon(initialTheme);

    // Добавляем кнопку в шапку (например, в .auth-info)
    const authInfoDiv = document.querySelector('.auth-info');
    if (authInfoDiv) {
        authInfoDiv.insertBefore(toggleButton, authInfoDiv.firstChild); // Вставим первой
    } else {
        // Если .auth-info нет, можно вставить в .app-header-content
        const headerContent = document.querySelector('.app-header-content');
        if (headerContent) {
            headerContent.appendChild(toggleButton);
        }
    }

    // Обработчик клика
    toggleButton.addEventListener('click', function () {
        let currentTheme = document.documentElement.getAttribute('data-theme');
        let newTheme;

        if (currentTheme === 'dark') {
            newTheme = 'light';
        } else {
            newTheme = 'dark';
        }

        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateButtonIcon(newTheme);
    });

    // Обновление иконки
    function updateButtonIcon(theme) {
        if (theme === 'dark') {
            toggleButton.innerHTML = '☀️'; // Солнце для светлой темы
        } else {
            toggleButton.innerHTML = '🌙'; // Луна для тёмной темы
        }
    }

    // Обновление при изменении системной темы (если пользователь не выбрал тему вручную)
    if (!savedTheme) {
        window.matchMedia('(prefers-color-scheme: dark)')
            .addEventListener('change', function(e) {
                const newTheme = e.matches ? 'dark' : 'light';
                document.documentElement.setAttribute('data-theme', newTheme);
                updateButtonIcon(newTheme);
            });
    }
});