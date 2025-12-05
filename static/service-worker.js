const CACHE_NAME = 'notebook-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js', // Если используется
  '/static/tinymce/tinymce.min.js', // Добавьте пути к ресурсам редактора
  // Добавьте другие важные файлы, которые должны работать оффлайн
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Возвращаем кэшированный ресурс, если он есть
        if (response) {
          return response;
        }
        // Иначе, делаем сетевой запрос
        return fetch(event.request);
      }
    )
  );
});