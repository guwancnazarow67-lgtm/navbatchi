/* Web Push: Service Worker + Push API */
(function () {
  'use strict';
  var NAV = (window.NAV = window.NAV || {});
  var supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  var vapid = document.body.dataset.vapid;

  function urlB64ToUint8Array(b64) {
    var pad = '='.repeat((4 - (b64.length % 4)) % 4);
    var base = (b64 + pad).replace(/-/g, '+').replace(/_/g, '/');
    var raw = atob(base), out = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }

  var swReady = null;
  function registerSW() {
    if (!('serviceWorker' in navigator)) return Promise.resolve(null);
    if (!swReady) swReady = navigator.serviceWorker.register('/sw.js').then(function () { return navigator.serviceWorker.ready; }).catch(function () { return null; });
    return swReady;
  }

  async function currentSubscription() {
    if (!supported) return null;
    var reg = await registerSW();
    return reg ? reg.pushManager.getSubscription() : null;
  }

  async function subscribe() {
    if (!supported) throw new Error("Bu brauzer bildirishnomalarni qo'llab-quvvatlamaydi");
    var perm = await Notification.requestPermission();
    if (perm !== 'granted') throw new Error('Bildirishnomaga ruxsat berilmadi');
    var reg = await registerSW();
    if (!reg) throw new Error("Service Worker ishga tushmadi (HTTPS kerak bo'lishi mumkin)");
    var sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlB64ToUint8Array(vapid) });
    }
    await NAV.api('POST', '/api/push/subscribe', { subscription: sub.toJSON() });
    return sub;
  }

  async function unsubscribe() {
    var sub = await currentSubscription();
    var endpoint = sub ? sub.endpoint : null;
    if (sub) { try { await sub.unsubscribe(); } catch (e) { /* ignore */ } }
    await NAV.api('POST', '/api/push/unsubscribe', endpoint ? { endpoint: endpoint } : {});
  }

  NAV.push = {
    supported: supported,
    permission: function () { return supported ? Notification.permission : 'unsupported'; },
    current: currentSubscription,
    subscribe: subscribe,
    unsubscribe: unsubscribe,
    isIOS: /iphone|ipad|ipod/i.test(navigator.userAgent),
    isStandalone: (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) || window.navigator.standalone === true
  };

  // Foydalanuvchi sahifalarida Service Worker doim ro'yxatdan o'tadi
  if (document.body.dataset.role === 'user') registerSW();
})();
