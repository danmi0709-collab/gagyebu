// 나만의 가계부 Service Worker
const CACHE_NAME = 'gagyebu-v2';  // 버전 올리면 이전 캐시 자동 삭제

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

// 네트워크 요청: 항상 네트워크 먼저 → 실패 시 캐시 (오프라인 대비)
self.addEventListener('fetch', (e) => {
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        // 성공 시 캐시 갱신
        if (res && res.status === 200 && e.request.method === 'GET') {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request))  // 오프라인이면 캐시에서
  );
});
