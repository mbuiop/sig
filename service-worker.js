const CACHE_NAME = 'galactic-warfare-v1';
const urlsToCache = [
    '/',
    '/index.html',
    '/manifest.json',
    '/js/main.js',
    '/js/engine/GameEngine.js',
    '/js/engine/Renderer.js',
    '/js/engine/Physics.js',
    '/js/engine/AudioManager.js',
    '/js/engine/InputManager.js',
    '/js/game/Player.js',
    '/js/game/Enemy.js',
    '/js/game/Bullet.js',
    '/js/game/Particle.js',
    '/js/game/Level.js',
    '/js/managers/GameManager.js',
    '/js/managers/AssetManager.js',
    '/js/managers/UIManager.js',
    '/js/utils/Utils.js',
    '/js/utils/Storage.js',
    '/assets/icons/icon-192.png',
    '/assets/icons/icon-512.png'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                return cache.addAll(urlsToCache);
            })
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                return fetch(event.request);
            }
        )
    );
});
