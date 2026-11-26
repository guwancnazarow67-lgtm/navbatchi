(function () {
  'use strict';
  var form = document.getElementById('password-form');
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var f = form.elements;
    if (f.new.value !== f.again.value) { NAV.toast('Yangi parollar mos kelmadi', 'error'); return; }
    NAV.busy(form.querySelector('button[type=submit]'), async function () {
      await NAV.api('POST', '/api/admin/account/password', { current: f.current.value, new: f.new.value });
      form.reset();
      NAV.toast('Parol almashtirildi', 'success');
    });
  });
})();
