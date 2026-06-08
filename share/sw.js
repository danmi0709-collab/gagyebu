// 나만의 가계부 Service Worker
const CACHE_NAME = 'gagyebu-v1';
const ASSETS = [
  './',
  './index.html',
];

// 설치: 핵심 파일 캐시
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

// 활성화: 이전 캐시 정리
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// 네트워크 요청 처리 (Network First → 오프라인 시 캐시 사용)
self.addEventListener('fetch', (e) => {
  // CDN 등 외부 리소스: 네트워크 우선, 실패 시 캐시
  if (!e.request.url.includes(self.location.origin)) {
    e.respondWith(
      fetch(e.request).catch(() => caches.match(e.request))
    );
    return;
  }

  // 로컬 리소스: 캐시 우선, 없으면 네트워크
  e.respondWith(
    caches.match(e.request).then((cached) => {
      if (cached) return cached;
      return fetch(e.request).then((res) => {
        if (res && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(e.request, clone));
        }
        return res;
      });
    })
  );
});
