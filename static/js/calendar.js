/* Oylik kalendar: foydalanuvchi va administrator rejimlari */
(function () {
  'use strict';
  var DOW = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya'];

  function hue(id) { return 'hsl(' + ((id * 47) % 360) + ' 62% 42%)'; }

  NAV.Calendar = function (root, opts) {
    var today = opts.today;
    var cur = NAV.parseISO(today);
    cur.setDate(1);
    var byDate = {};

    function gridRange() {
      var first = new Date(cur.getFullYear(), cur.getMonth(), 1);
      var offset = (first.getDay() + 6) % 7; // dushanba = 0
      var start = new Date(first); start.setDate(1 - offset);
      var end = new Date(start); end.setDate(start.getDate() + 41);
      return { start: start, end: end };
    }

    async function load() {
      var r = gridRange();
      try {
        var res = await NAV.api('GET', opts.url + '?start=' + NAV.iso(r.start) + '&end=' + NAV.iso(r.end));
        byDate = {};
        (res.items || []).forEach(function (it) { (byDate[it.date] = byDate[it.date] || []).push(it); });
      } catch (e) { NAV.toast(e.message, 'error'); }
      render();
    }

    function btn(text, label, fn) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'btn btn-ghost btn-sm'; b.textContent = text; b.setAttribute('aria-label', label);
      b.addEventListener('click', fn);
      return b;
    }

    function render() {
      root.replaceChildren();
      var head = document.createElement('div'); head.className = 'cal-head';
      var title = document.createElement('div'); title.className = 'cal-title';
      title.textContent = NAV.MONTHS[cur.getMonth()] + ' ' + cur.getFullYear();
      var nav = document.createElement('div'); nav.className = 'cal-nav';
      nav.appendChild(btn('‹', 'Oldingi oy', function () { cur.setMonth(cur.getMonth() - 1); load(); }));
      nav.appendChild(btn('Bugun', 'Bugungi oy', function () { cur = NAV.parseISO(today); cur.setDate(1); load(); }));
      nav.appendChild(btn('›', 'Keyingi oy', function () { cur.setMonth(cur.getMonth() + 1); load(); }));
      head.appendChild(title); head.appendChild(nav); root.appendChild(head);

      var grid = document.createElement('div'); grid.className = 'cal-grid';
      DOW.forEach(function (d) { var c = document.createElement('div'); c.className = 'cal-dow'; c.textContent = d; grid.appendChild(c); });

      var r = gridRange();
      for (var i = 0; i < 42; i++) {
        var d = new Date(r.start); d.setDate(r.start.getDate() + i);
        var ds = NAV.iso(d);
        var items = byDate[ds] || [];
        var cell = document.createElement(opts.mode === 'admin' ? 'button' : 'div');
        if (opts.mode === 'admin') cell.type = 'button';
        cell.className = 'cal-day';
        if (d.getMonth() !== cur.getMonth()) cell.classList.add('other');
        if (ds === today) cell.classList.add('today');
        var num = document.createElement('span'); num.className = 'num'; num.textContent = d.getDate();
        cell.appendChild(num);

        if (opts.mode === 'user') {
          if (items.length) {
            cell.classList.add(ds < today ? 'past' : 'future');
            var tag = document.createElement('span'); tag.className = 'tag'; tag.textContent = 'Navbatchi';
            cell.appendChild(tag);
            cell.title = (ds < today ? "O'tgan" : 'Kelgusi') + ' navbatchilik: ' + NAV.fmtDate(ds);
          }
        } else {
          items.slice(0, 2).forEach(function (it) {
            var w = document.createElement('span'); w.className = 'who'; w.textContent = it.name;
            w.style.background = hue(it.user_id); cell.appendChild(w);
          });
          if (items.length > 2) { var more = document.createElement('span'); more.className = 'more'; more.textContent = '+' + (items.length - 2) + ' yana'; cell.appendChild(more); }
          (function (dateStr) {
            cell.addEventListener('click', function () { if (opts.onDay) opts.onDay(dateStr, byDate[dateStr] || []); });
          })(ds);
        }
        grid.appendChild(cell);
      }
      root.appendChild(grid);
    }

    load();
    return { reload: load, items: function (ds) { return byDate[ds] || []; } };
  };

  NAV.userHue = hue;
})();
