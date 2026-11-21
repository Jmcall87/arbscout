const CACHE = 'arbscout-v1';

const CORE = [
  './',
  './index.html',
  './styles.css',
  './app.js',
  './manifest.webmanifest',
  './assets/icon.svg',
  './assets/fonts/inter-latin-variable.woff2',
  './assets/hdri/blocky_photo_studio_1k.hdr',
  './assets/models/camera/Camera_01_1k.gltf',
  './assets/models/camera/Camera_01.bin',
  './vendor/three.module.js',
  './vendor/GLTFLoader.js',
  './vendor/RGBELoader.js',
];

const TEXTURES = [
  'Camera_01_body_arm_1k', 'Camera_01_body_diff_1k', 'Camera_01_body_nor_gl_1k',
  'Camera_01_lens_body_arm_1k', 'Camera_01_lens_body_diff_1k', 'Camera_01_lens_body_nor_gl_1k',
  'Camera_01_strap_arm_1k', 'Camera_01_strap_diff_1k', 'Camera_01_strap_nor_gl_1k',
].map((name) => `./assets/models/camera/textures/${name}.jpg`);

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then(async (cache) => {
      await Promise.all(
        [...CORE, ...TEXTURES].map((url) => cache.add(url).catch(() => undefined))
      );
      await self.skipWaiting();
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.pathname.includes('/api/')) {
    event.respondWith(fetch(request));
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
