/* NAVBATCHI Service Worker — Web Push */
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (event) { event.waitUntil(self.clients.claim()); });

self.addEventListener('push', function (event) {
  var data = {};
  try { data = event.data ? event.data.json() : {}; }
  catch (e) { data = { title: 'NAVBATCHI', body: event.data ? event.data.text() : '' }; }
  var title = data.title || 'NAVBATCHI';
  event.waitUntil(self.registration.showNotification(title, {
    body: data.body || '',
    icon: '/static/img/icon-192.png',
    badge: '/static/img/icon-192.png',
    tag: data.tag || 'navbatchi',
    data: { url: data.url || '/app' }
  }));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var target = new URL((event.notification.data && event.notification.data.url) || '/app', self.location.origin).href;
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
    for (var i = 0; i < list.length; i++) {
      if (list[i].url.indexOf(self.location.origin) === 0 && 'focus' in list[i]) {
        list[i].navigate(target);
        return list[i].focus();
      }
    }
    return self.clients.openWindow(target);
  }));
});
