(function () {
  'use strict';
  var form = document.getElementById('notify-form');
  var pick = document.getElementById('pick-list');
  form.querySelectorAll('input[name=target]').forEach(function (r) {
    r.addEventListener('change', function () { pick.hidden = form.elements.target.value !== 'selected'; });
  });
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var f = form.elements, all = f.target.value === 'all';
    var ids = Array.prototype.slice.call(form.querySelectorAll('input[name=user]:checked')).map(function (c) { return parseInt(c.value, 10); });
    if (!all && !ids.length) { NAV.toast('Kamida bitta foydalanuvchini tanlang', 'error'); return; }
    NAV.busy(form.querySelector('button[type=submit]'), async function () {
      var r = await NAV.api('POST', '/api/admin/notify', { title: f.title.value, body: f.body.value, all: all, user_ids: ids });
      NAV.toast('Yuborildi: ' + r.total + ' ta foydalanuvchi, push: ' + r.pushed, 'success');
      setTimeout(function () { location.reload(); }, 900);
    });
  });
})();
