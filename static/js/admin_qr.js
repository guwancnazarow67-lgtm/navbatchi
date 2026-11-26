(function () {
  'use strict';
  var form = document.getElementById('qr-form');
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var f = form.elements;
    NAV.busy(form.querySelector('button[type=submit]'), async function () {
      await NAV.api('POST', '/api/admin/qr', { label: f.label.value, valid_days: parseInt(f.valid_days.value || '0', 10) });
      location.reload();
    });
  });
  document.querySelectorAll('.qr-card').forEach(function (card) {
    card.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-act]');
      if (!b) return;
      var id = card.dataset.id, act = b.dataset.act;
      if (act === 'copy') NAV.copy(b.dataset.link);
      if (act === 'toggle') NAV.busy(b, async function () {
        await NAV.api('PATCH', '/api/admin/qr/' + id, { active: b.dataset.active !== '1' });
        location.reload();
      });
      if (act === 'delete') {
        if (!confirm("QR-kod o'chirilsinmi? Bu QR-kod bilan ro'yxatdan o'tgan foydalanuvchilar o'chmaydi, lekin QR endi ishlamaydi.")) return;
        NAV.busy(b, async function () { await NAV.api('DELETE', '/api/admin/qr/' + id); location.reload(); });
      }
    });
  });
})();
