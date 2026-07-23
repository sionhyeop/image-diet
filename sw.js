/* 이미지 변환 — 오프라인 캐시 서비스 워커 */
var CACHE = 'image-diet-v29';        /* 앱 셸 — 배포마다 새 버전으로 교체 */
/* 모델·런타임 바이너리(models/, vendor/)는 파일 내용이 바뀌지 않으므로 앱 버전과
   분리된 캐시에 둔다. 앱을 새로 배포해도 지워지지 않아 재다운로드가 없다. */
var BIN = 'image-diet-bin-v1';
/* 'sam-models-v1'은 index.html이 외부 CDN 모델(RMBG·SlimSAM)을 직접 넣는 캐시다.
   여기서 지우면 새로 배포할 때마다 42MB를 다시 받게 되므로 반드시 보존한다. */
var KEEP = [CACHE, BIN, 'sam-models-v1'];
var ASSETS = ['./', './index.html', './manifest.json', './icon.svg', './icon-180.png', './icon-192.png', './icon-512.png'];

function isBinary(url) {
  return /\/(models|vendor)\//.test(url.pathname);
}

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
        return Promise.all(
          keys.filter(function (k) { return KEEP.indexOf(k) < 0; })
              .map(function (k) { return caches.delete(k); })
        );
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

  /* AI 모델·ONNX 런타임은 캐시 우선(재검증 없음) — 한 번 받으면 다시 내려받지 않는다.
     stale-while-revalidate로 두면 캐시로 응답하면서도 매번 11MB wasm·4.5MB 모델을
     백그라운드로 다시 받는다. */
  if (isBinary(url)) {
    e.respondWith(
      caches.open(BIN).then(function (c) {
        return c.match(req).then(function (cached) {
          if (cached) return cached;
          return fetch(req).then(function (res) {
            if (res && res.ok) c.put(req, res.clone());
            return res;
          });
        });
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
