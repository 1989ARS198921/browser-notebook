// static/js/theme-toggle.js
(function() {
    'use strict';

    const themeToggleBtn = document.createElement('button');
    themeToggleBtn.className = 'btn btn-secondary theme-toggle-btn';
    themeToggleBtn.setAttribute('aria-label', 'Переключить тему');
    themeToggleBtn.innerHTML = '🌙'; // Иконка луны по умолчанию

    const storedTheme = localStorage.getItem('theme');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');

    // Установка начальной темы
    if (storedTheme !== null) {
        document.documentElement.setAttribute('data-theme', storedTheme);
        if (storedTheme === 'dark') {
            themeToggleBtn.innerHTML = '☀️'; // Иконка солнца, если темная
        }
    } else {
        // Если нет сохраненной темы, проверяем системную
        if (prefersDarkScheme.matches) {
            document.documentElement.setAttribute('data-theme', 'dark');
            themeToggleBtn.innerHTML = '☀️';
        }
    }

    // Обработчик переключения
    themeToggleBtn.addEventListener('click', function() {
        let currentTheme = document.documentElement.getAttribute('data-theme');

        if (currentTheme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
            themeToggleBtn.innerHTML = '🌙';
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            themeToggleBtn.innerHTML = '☀️';
        }
    });

    // Добавляем кнопку в шапку или в боковую панель
    // Найдем место для кнопки, например, внутрь .auth-info
    const authInfoDiv = document.querySelector('.auth-info');
    if (authInfoDiv) {
        // Вставим кнопку перед первым элементом или в конец
        // authInfoDiv.insertBefore(themeToggleBtn, authInfoDiv.firstChild); // Перед первым
        authInfoDiv.appendChild(themeToggleBtn); // В конец
    } else {
        // Или добавим в шапку, если .auth-info нет
        const headerContent = document.querySelector('.app-header-content');
        if (headerContent) {
            headerContent.appendChild(themeToggleBtn);
        }
    }


    // Обновление иконки при изменении системной темы (опционально)
    // Это сработает, только если пользователь не выбрал тему вручную
    if (storedTheme === null) {
        prefersDarkScheme.addEventListener('change', (e) => {
            if (e.matches) {
                document.documentElement.setAttribute('data-theme', 'dark');
                themeToggleBtn.innerHTML = '☀️';
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                themeToggleBtn.innerHTML = '🌙';
            }
        });
    }

})();