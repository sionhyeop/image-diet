/* 이미지 변환 — 오프라인 캐시 서비스 워커 */
var CACHE = 'image-diet-v21';
var ASSETS = ['./', './index.html', './manifest.json', './icon.svg', './icon-180.png', './icon-192.png', './icon-512.png'];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE)
      .then(function (c) { return c.addAll(ASSETS); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;

  /* HTML(페이지 진입)은 네트워크 우선 — 배포 즉시 새 버전, 오프라인일 때만 캐시 */
  if (req.mode === 'navigate' || req.destination === 'document') {
    e.respondWith(
      fetch(req).then(function (res) {
        if (res && res.ok) {
          var clone = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, clone); });
        }
        return res;
      }).catch(function () {
        return caches.match(req).then(function (r) { return r || caches.match('./index.html'); });
      })
    );
    return;
  }

  /* 그 외 자산은 stale-while-revalidate */
  e.respondWith(
    caches.match(req).then(function (cached) {
      var fresh = fetch(req).then(function (res) {
        if (res && res.ok) {
          var clone = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, clone); });
        }
        return res;
      }).catch(function () { return cached; });
      return cached || fresh;
    })
  );
});
