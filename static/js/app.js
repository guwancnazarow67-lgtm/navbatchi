/* NAVBATCHI — umumiy yordamchilar */
(function () {
  'use strict';
  var meta = document.querySelector('meta[name="csrf-token"]');
  var csrf = meta ? meta.content : '';
  var NAV = (window.NAV = window.NAV || {});

  NAV.MONTHS = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentyabr', 'oktyabr', 'noyabr', 'dekabr'];
  NAV.WEEKDAYS = ['Yakshanba', 'Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba'];

  NAV.api = async function (method, url, data) {
    var opts = { method: method, credentials: 'same-origin', headers: { 'X-CSRF-Token': csrf, 'Accept': 'application/json' } };
    if (data !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(data);
    }
    var res;
    try { res = await fetch(url, opts); } catch (e) { throw new Error("Server bilan aloqa yo'q"); }
    var json = null;
    try { json = await res.json(); } catch (e) { /* bo'sh javob */ }
    if (res.status === 401) { location.reload(); throw new Error('Sessiya tugagan'); }
    if (!res.ok || (json && json.ok === false)) {
      throw new Error((json && json.error) || 'Xatolik yuz berdi');
    }
    return json || {};
  };

  NAV.toast = function (message, type) {
    var box = document.getElementById('toasts');
    if (!box) return;
    var el = document.createElement('div');
    el.className = 'toast ' + (type || '');
    el.textContent = message;
    box.appendChild(el);
    setTimeout(function () { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; }, 3200);
    setTimeout(function () { el.remove(); }, 3600);
  };

  NAV.openModal = function (id) {
    var m = document.getElementById(id);
    if (m) { m.hidden = false; var f = m.querySelector('input:not([type=hidden]), select, textarea'); if (f) setTimeout(function () { f.focus(); }, 30); }
  };
  NAV.closeModal = function (el) {
    var m = typeof el === 'string' ? document.getElementById(el) : el.closest('.modal');
    if (m) m.hidden = true;
  };
  document.addEventListener('click', function (e) {
    var closer = e.target.closest('[data-modal-close]');
    if (closer) NAV.closeModal(closer);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') document.querySelectorAll('.modal:not([hidden])').forEach(function (m) { m.hidden = true; });
  });

  NAV.copy = async function (text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch (e) {
      var ta = document.createElement('textarea');
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (err) { /* ignore */ }
      ta.remove();
    }
    NAV.toast('Nusxalandi', 'success');
  };

  NAV.busy = async function (btn, fn) {
    if (btn) btn.disabled = true;
    try { return await fn(); }
    catch (e) { NAV.toast(e.message, 'error'); }
    finally { if (btn) btn.disabled = false; }
  };

  NAV.pad = function (n) { return String(n).padStart(2, '0'); };
  NAV.iso = function (d) { return d.getFullYear() + '-' + NAV.pad(d.getMonth() + 1) + '-' + NAV.pad(d.getDate()); };
  NAV.parseISO = function (s) { var p = s.split('-').map(Number); return new Date(p[0], p[1] - 1, p[2]); };
  NAV.fmtDate = function (s) { var d = NAV.parseISO(s); return d.getDate() + '-' + NAV.MONTHS[d.getMonth()] + ', ' + d.getFullYear(); };
  NAV.pageData = function () {
    var el = document.getElementById('page-data');
    try { return el ? JSON.parse(el.textContent) : {}; } catch (e) { return {}; }
  };

  // Dark / Light rejim
  function setTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem('theme', t); } catch (e) {}
    var m = document.querySelector('meta[name="theme-color"]');
    if (m) m.content = t === 'dark' ? '#0e111f' : '#5b6cff';
  }
  document.addEventListener('click', function (e) {
    var tgl = e.target.closest('[data-theme-toggle]');
    if (tgl) { setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark'); return; }
    var set = e.target.closest('[data-theme-set]');
    if (set) setTheme(set.getAttribute('data-theme-set'));
  });

  // Mobil menyu (admin)
  var sb = document.getElementById('sidebar'), scrim = document.getElementById('scrim');
  function toggleSidebar(open) {
    if (!sb) return;
    sb.classList.toggle('open', open);
    if (scrim) scrim.classList.toggle('open', open);
  }
  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-sidebar-toggle]')) toggleSidebar(!sb.classList.contains('open'));
    else if (e.target === scrim) toggleSidebar(false);
  });
})();
