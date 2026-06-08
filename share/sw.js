// 나만의 가계부 Service Worker
const CACHE_NAME = 'gagyebu-v3';  // 버전 올리면 이전 캐시 자동 삭제

// 설치: 핵심 파일 캐시
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(['./index.html']))
  );
  self.skipWaiting();  // 즉시 활성화
});

// 활성화: 이전 버전 캐시 전부 삭제
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();  // 열려있는 탭도 즉시 새 SW 적용
});

// 네트워크 요청: HTTP 캐시 무시하고 항상 서버에서 새로 받음 → 실패 시 캐시
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;

  const isLocal = e.request.url.startsWith(self.location.origin);

  e.respondWith(
    fetch(e.request, isLocal ? { cache: 'no-cache' } : {})
      .then((res) => {
        if (res && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
