// 通信が無くても開けるようにする。版 129a87f518
// つながっているときは必ず最新を取りに行き、手元の保存分は通信できないときだけ使う
const CACHE = "kanji-129a87f518";
const FILES = ["./", "index.html", "manifest.webmanifest", "icon-180.png", "icon-192.png", "icon-512.png"];
self.addEventListener("install", e => {
  // cache: "reload" … ブラウザの一時保存（GitHubは10分間）を通さず、最新を取る
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES.map(f => new Request(f, { cache: "reload" })))));
  self.skipWaiting();
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.hostname.endsWith("google.com") || u.hostname.endsWith("googleusercontent.com")) return;
  if (u.origin === location.origin) {
    // 自分のファイル：まず最新を取りに行く。だめなら手元の保存分
    e.respondWith(fetch(e.request, { cache: "no-cache" }).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
      return res;
    }).catch(() => caches.match(e.request).then(hit => hit || caches.match("./"))));
    return;
  }
  // フォント：変わらないので手元の保存分を先に使う
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
    if (res.ok || res.type === "opaque") { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
    return res;
  })));
});
