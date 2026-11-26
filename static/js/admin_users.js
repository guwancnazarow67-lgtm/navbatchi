(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var form = $('user-form');

  // qidiruv
  var search = $('user-search');
  if (search) search.addEventListener('input', function () {
    var q = search.value.trim().toLowerCase();
    document.querySelectorAll('#user-table tbody tr').forEach(function (tr) {
      tr.hidden = q && tr.dataset.search.indexOf(q) === -1;
    });
  });

  function openForm(data) {
    form.reset();
    form.elements.id.value = data ? data.id : '';
    form.elements.first_name.value = data ? data.first : '';
    form.elements.last_name.value = data ? data.last : '';
    form.elements.phone.value = data ? data.phone : '';
    form.elements.note.value = data ? data.note : '';
    form.elements.active.checked = data ? data.active === '1' : true;
    $('active-wrap').hidden = !data;
    $('user-modal-title').textContent = data ? 'Foydalanuvchini tahrirlash' : "Yangi foydalanuvchi";
    NAV.openModal('user-modal');
  }
  function showLink(link) {
    $('link-value').value = link;
    NAV.openModal('link-modal');
  }

  $('user-add').addEventListener('click', function () { openForm(null); });
  $('link-copy').addEventListener('click', function () { NAV.copy($('link-value').value); });
  // havola oynasi yopilganda ro'yxatni yangilaymiz
  $('link-modal').addEventListener('click', function (e) { if (e.target.closest('[data-modal-close]')) location.reload(); });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var f = form.elements, id = f.id.value;
    var body = { first_name: f.first_name.value, last_name: f.last_name.value, phone: f.phone.value, note: f.note.value, active: f.active.checked };
    NAV.busy(form.querySelector('button[type=submit]'), async function () {
      if (id) {
        await NAV.api('PUT', '/api/admin/users/' + id, body);
        location.reload();
      } else {
        var r = await NAV.api('POST', '/api/admin/users', body);
        NAV.closeModal('user-modal');
        showLink(r.link);
      }
    });
  });

  var table = $('user-table');
  if (table) table.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-act]');
    if (!b) return;
    var tr = b.closest('tr'), id = tr.dataset.id, act = b.dataset.act;
    if (act === 'edit') openForm(tr.dataset);
    if (act === 'delete') {
      if (!confirm("«" + tr.dataset.first + ' ' + tr.dataset.last + "» o'chirilsinmi? Uning navbatchilik sanalari ham o'chadi.")) return;
      NAV.busy(b, async function () { await NAV.api('DELETE', '/api/admin/users/' + id); location.reload(); });
    }
    if (act === 'link') {
      if (!confirm("Yangi shaxsiy havola yaratilsa, foydalanuvchining eski havolasi ishlamay qoladi. Davom etasizmi?")) return;
      NAV.busy(b, async function () { var r = await NAV.api('POST', '/api/admin/users/' + id + '/link'); showLink(r.link); });
    }
  });
})();
