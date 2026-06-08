// 나만의 가계부 Service Worker
const CACHE_NAME = 'gagyebu-v8';  // deploy.py가 자동으로 올림
const RELEASE_NOTES = '하단 탭 클릭 안되는 버그 수정 (설치배너 pointer-events 수정)';          // deploy.py가 커밋 메시지로 자동 채움

// 설치
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(['./index.html']))
  );
  // skipWaiting 안 함 — 앱이 "새 버전 있음" 배너 보여준 뒤 사용자가 승인할 때 활성화
});

// 활성화: 이전 캐시 삭제
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// 네트워크 우선 (HTTP 캐시 무시)
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

// 메시지 핸들러
self.addEventListener('message', (e) => {
  // 앱에서 "지금 새로고침" 눌렀을 때
  if (e.data && e.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  // 앱에서 릴리즈 노트 요청
  if (e.data && e.data.type === 'GET_RELEASE_NOTES') {
    e.ports[0].postMessage({ type: 'RELEASE_NOTES', notes: RELEASE_NOTES });
  }
});
