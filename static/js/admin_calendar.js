(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var data = NAV.pageData();
  var users = data.users || [];
  var cal, selected = null;

  function renderDay(ds, items) {
    selected = ds;
    var d = NAV.parseISO(ds);
    $('day-title').textContent = NAV.fmtDate(ds) + ' · ' + NAV.WEEKDAYS[d.getDay()];
    var list = $('day-list'); list.replaceChildren();
    $('day-empty').hidden = items.length > 0;
    items.forEach(function (it) {
      var li = document.createElement('li'); li.className = 'duty-row';
      var left = document.createElement('div');
      var dot = document.createElement('span'); dot.className = 'dot'; dot.style.background = NAV.userHue(it.user_id);
      var b = document.createElement('b'); b.textContent = it.name;
      left.appendChild(dot); left.appendChild(b);
      if (it.note) { var s = document.createElement('small'); s.textContent = it.note; left.appendChild(s); }
      var act = document.createElement('div'); act.className = 'duty-actions';
      var date = document.createElement('input'); date.type = 'date'; date.className = 'input small-input'; date.value = ds; date.hidden = true; date.style.margin = '0'; date.style.width = 'auto';
      var move = document.createElement('button'); move.type = 'button'; move.className = 'btn btn-ghost btn-sm'; move.textContent = "Ko'chirish";
      var del = document.createElement('button'); del.type = 'button'; del.className = 'btn btn-danger btn-sm'; del.textContent = "O'chirish";
      move.addEventListener('click', function () {
        if (date.hidden) { date.hidden = false; move.textContent = 'Saqlash'; return; }
        if (!date.value || date.value === ds) { date.hidden = true; move.textContent = "Ko'chirish"; return; }
        NAV.busy(move, async function () {
          await NAV.api('PUT', '/api/admin/duties/' + it.id, { duty_date: date.value });
          NAV.toast("Boshqa kunga ko'chirildi", 'success'); await cal.reload(); renderDay(ds, cal.items(ds));
        });
      });
      del.addEventListener('click', function () {
        if (!confirm("«" + it.name + "» ning bu kundagi navbatchiligi o'chirilsinmi?")) return;
        NAV.busy(del, async function () {
          await NAV.api('DELETE', '/api/admin/duties/' + it.id);
          NAV.toast("O'chirildi", 'success'); await cal.reload(); renderDay(ds, cal.items(ds));
        });
      });
      act.appendChild(date); act.appendChild(move); act.appendChild(del);
      li.appendChild(left); li.appendChild(act); list.appendChild(li);
    });
    $('day-form').reset();
    NAV.openModal('day-modal');
  }

  cal = NAV.Calendar($('calendar'), { mode: 'admin', url: $('calendar').dataset.url, today: $('calendar').dataset.today, onDay: renderDay });

  $('day-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var f = e.target.elements;
    NAV.busy(e.target.querySelector('button[type=submit]'), async function () {
      var r = await NAV.api('POST', '/api/admin/duties', { user_ids: [parseInt(f.user_id.value, 10)], dates: [selected], note: f.note.value });
      NAV.toast(r.added ? 'Biriktirildi' : 'Bu foydalanuvchi allaqachon biriktirilgan', r.added ? 'success' : 'error');
      await cal.reload(); renderDay(selected, cal.items(selected));
    });
  });

  // ommaviy biriktirish
  $('bulk-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var f = e.target.elements;
    var from = NAV.parseISO(f.from.value), to = NAV.parseISO(f.to.value), step = parseInt(f.step.value, 10) || 1;
    if (to < from) { NAV.toast("Tugash sanasi boshlanish sanasidan oldin bo'lmasin", 'error'); return; }
    var dates = [];
    for (var d = new Date(from); d <= to; d.setDate(d.getDate() + step)) dates.push(NAV.iso(d));
    if (dates.length > 366) { NAV.toast("Bir vaqtda 366 tadan ko'p sana biriktirib bo'lmaydi", 'error'); return; }
    NAV.busy(e.target.querySelector('button[type=submit]'), async function () {
      var r = await NAV.api('POST', '/api/admin/duties', { user_ids: [parseInt(f.user_id.value, 10)], dates: dates, note: f.note.value });
      NAV.toast(r.added + ' ta sana biriktirildi' + (r.skipped ? ' (' + r.skipped + " tasi avval bor edi)" : ''), 'success');
      cal.reload();
    });
  });
})();
