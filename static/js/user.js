/* Foydalanuvchi paneli sahifalari */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };

  // ---- Kalendar ----
  var calRoot = $('calendar');
  if (calRoot && calRoot.dataset.mode === 'user') {
    NAV.Calendar(calRoot, { mode: 'user', url: calRoot.dataset.url, today: calRoot.dataset.today });
  }

  // ---- Bildirishnomaga ruxsat so'rash oynasi (bosh sahifa) ----
  var card = $('push-card'), modal = $('push-modal');
  if (card && modal) {
    var asked = card.dataset.asked === '1', enabled = card.dataset.enabled === '1';
    var P = NAV.push;
    var text = $('push-card-text');

    function showCard(msg, withButton) {
      card.hidden = false;
      text.textContent = msg;
      if (withButton) {
        var b = document.createElement('button');
        b.className = 'btn btn-primary btn-sm'; b.type = 'button'; b.textContent = 'Yoqish';
        b.addEventListener('click', function () { askModal(); });
        text.appendChild(document.createElement('br'));
        text.appendChild(b);
      }
    }
    function askModal() {
      $('push-ios-hint').hidden = !(P.isIOS && !P.isStandalone);
      modal.hidden = false;
    }

    (async function init() {
      if (!P.supported) {
        if (P.isIOS && !P.isStandalone && !asked) askModal();
        return;
      }
      var perm = P.permission();
      if (perm === 'granted') {
        try {
          var sub = await P.current();
          if (!asked || (enabled && !sub)) await P.subscribe();
          else if (asked && !enabled) showCard("Bildirishnomalar yoqilmagan. Navbatchilik eslatmalarini olish uchun yoqing.", true);
        } catch (e) { /* jim */ }
        return;
      }
      if (perm === 'denied') {
        if (!asked) { try { await NAV.api('POST', '/api/push/decline'); } catch (e) {} }
        showCard("Bildirishnomalar brauzer sozlamalarida bloklangan. Ularni yoqish uchun sayt sozlamalarida ruxsat bering.", false);
        return;
      }
      if (!asked) askModal();
      else showCard("Bildirishnomalar yoqilmagan. Navbatchilik eslatmalarini olish uchun yoqing.", true);
    })();

    $('push-yes').addEventListener('click', function () {
      var btn = this;
      NAV.busy(btn, async function () {
        if (!P.supported) {
          modal.hidden = true;
          throw new Error(P.isIOS ? "Avval saytni «Ekranga qo'shish» orqali o'rnating" : "Bu brauzer bildirishnomalarni qo'llab-quvvatlamaydi");
        }
        try {
          await P.subscribe();
          modal.hidden = true; card.hidden = true;
          NAV.toast('Bildirishnomalar yoqildi', 'success');
        } catch (e) {
          modal.hidden = true;
          try { await NAV.api('POST', '/api/push/decline'); } catch (e2) {}
          throw e;
        }
      });
    });
    $('push-no').addEventListener('click', function () {
      NAV.busy(this, async function () {
        await NAV.api('POST', '/api/push/decline');
        modal.hidden = true;
        showCard("Bildirishnomalar yoqilmagan. Xohlasangiz, Profil bo'limidan yoqishingiz mumkin.", false);
      });
    });
  }

  // ---- Xabarlar sahifasi ----
  var mark = $('mark-read');
  if (mark) mark.addEventListener('click', function () {
    NAV.busy(mark, async function () { await NAV.api('POST', '/api/me/notifications/read'); location.reload(); });
  });

  // ---- Profil sahifasi ----
  var form = $('profile-form');
  if (form) form.addEventListener('submit', function (e) {
    e.preventDefault();
    var fd = Object.fromEntries(new FormData(form).entries());
    NAV.busy(form.querySelector('button[type=submit]'), async function () {
      await NAV.api('POST', '/api/me/profile', fd);
      NAV.toast("Ma'lumotlar saqlandi", 'success');
    });
  });

  var mk = $('make-link');
  if (mk) {
    mk.addEventListener('click', function () {
      if (!confirm("Yangi havola yaratilsa, eski havola ishlamay qoladi. Davom etasizmi?")) return;
      NAV.busy(mk, async function () {
        var r = await NAV.api('POST', '/api/me/link');
        $('link-value').value = r.link; $('link-box').hidden = false;
      });
    });
    $('link-copy').addEventListener('click', function () { NAV.copy($('link-value').value); });
  }

  var settings = $('push-settings');
  if (settings) {
    var P2 = NAV.push, status = $('push-status');
    var bEnable = $('push-enable'), bDisable = $('push-disable'), bTest = $('push-test');
    async function refresh() {
      bEnable.hidden = bDisable.hidden = bTest.hidden = true;
      if (!P2.supported) {
        status.textContent = P2.isIOS && !P2.isStandalone
          ? "iPhone'da bildirishnoma olish uchun saytni «Ulashish → Ekranga qo'shish» orqali o'rnating va ilovani shu yerdan oching."
          : "Bu brauzer bildirishnomalarni qo'llab-quvvatlamaydi.";
        return;
      }
      if (P2.permission() === 'denied') { status.textContent = "Bildirishnomalar brauzerda bloklangan. Sayt sozlamalaridan ruxsat bering."; return; }
      var sub = await P2.current();
      if (sub && P2.permission() === 'granted') {
        status.textContent = 'Bu qurilmada bildirishnomalar yoqilgan.';
        bDisable.hidden = false; bTest.hidden = false;
      } else {
        status.textContent = "Bu qurilmada bildirishnomalar yoqilmagan.";
        bEnable.hidden = false;
      }
    }
    bEnable.addEventListener('click', function () { NAV.busy(bEnable, async function () { await P2.subscribe(); NAV.toast('Yoqildi', 'success'); await refresh(); }); });
    bDisable.addEventListener('click', function () { NAV.busy(bDisable, async function () { await P2.unsubscribe(); NAV.toast("O'chirildi", 'success'); await refresh(); }); });
    bTest.addEventListener('click', function () { NAV.busy(bTest, async function () { await NAV.api('POST', '/api/me/test-push'); NAV.toast('Sinov xabari yuborildi', 'success'); }); });
    refresh();
  }
})();
