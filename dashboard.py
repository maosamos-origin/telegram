"""Read-only chart dashboard page for the paper XAUUSD monitor (no trading actions)."""

DASHBOARD_HTML = r"""<!doctype html>
<html lang="km">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>XAUUSD Signal Chart</title>
<style>
  :root { --bg:#0e1116; --card:#171b22; --line:#262c36; --text:#e6e9ef; --mute:#8b94a3;
          --buy:#22c55e; --sell:#ef4444; --entry:#60a5fa; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
         font-family:system-ui,-apple-system,"Noto Sans Khmer","Khmer OS",sans-serif;
         padding:env(safe-area-inset-top,0) 12px env(safe-area-inset-bottom,0); }
  header { display:flex; flex-wrap:wrap; gap:8px; align-items:center; justify-content:space-between; padding:12px 0; }
  h1 { font-size:18px; margin:0; }
  .pill { font-size:12px; padding:4px 10px; border-radius:999px; background:var(--card); border:1px solid var(--line); color:var(--mute); }
  .pill.ok { color:var(--buy); } .pill.bad { color:var(--sell); }
  #chart { width:100%; height:58vh; min-height:320px; background:var(--card); border:1px solid var(--line); border-radius:12px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:8px; margin:10px 0; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:10px 12px; }
  .card small { color:var(--mute); display:block; margin-bottom:2px; font-size:12px; }
  .card b { font-size:16px; font-variant-numeric:tabular-nums; }
  .buy { color:var(--buy); } .sell { color:var(--sell); } .entry { color:var(--entry); }
  #active { margin:10px 0; }
  .warn { color:var(--mute); font-size:12px; text-align:center; padding:10px 0 16px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th,td { text-align:left; padding:6px 4px; border-bottom:1px solid var(--line); font-variant-numeric:tabular-nums; }
  th { color:var(--mute); font-weight:500; }
  .scroll { overflow-x:auto; }
</style>
</head>
<body>
<header>
  <h1>🥇 XAUUSD • ក្រាហ្វសញ្ញា</h1>
  <div><span class="pill" id="st">កំពុងផ្ទុក…</span> <span class="pill" id="mode"></span> <span class="pill" id="scan"></span></div>
</header>
<div id="chart"></div>
<div id="active"></div>
<div class="card scroll"><small>សញ្ញាក្នុងចន្លោះទិន្នន័យថ្មីៗ (ម៉ោងភ្នំពេញ)</small>
  <table><thead><tr><th>ម៉ោង</th><th>ប្រភេទ</th><th>ចូល</th><th>SL</th><th>TP</th><th>លទ្ធផល</th></tr></thead><tbody id="rows"></tbody></table>
</div>
<div class="warn">⚠️ សញ្ញាសាកល្បង (Paper) • មិនមែនជាដំបូន្មានវិនិយោគ • ម៉ោងបង្ហាញជាម៉ោងភ្នំពេញ (UTC+7)</div>

<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function () {
  var OFFSET = 7 * 3600;            // show Cambodia time
  var params = new URLSearchParams(location.search);
  var key = params.get('key');
  var apiUrl = '/api/chart' + (key ? '?key=' + encodeURIComponent(key) : '');
  var $ = function (id) { return document.getElementById(id); };

  var chart = LightweightCharts.createChart($('chart'), {
    layout: { background: { color: '#171b22' }, textColor: '#aab2c0' },
    grid: { vertLines: { color: '#222833' }, horzLines: { color: '#222833' } },
    timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#2b323d', barSpacing: 8, minBarSpacing: 3, rightOffset: 6 },
    rightPriceScale: { borderColor: '#2b323d', scaleMargins: { top: 0.12, bottom: 0.12 } },
    crosshair: { mode: 0 },
    autoSize: true
  });
  var candles = chart.addCandlestickSeries({
    upColor: '#22c55e', downColor: '#ef4444', borderVisible: false,
    wickUpColor: '#22c55e', wickDownColor: '#ef4444'
  });
  var first = true;
  var overlays = [];   // line series for signal levels
  var priceLines = []; // axis labels for active signal

  function fmt(n) { return Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function hhmm(t) {
    var d = new Date((t + OFFSET) * 1000);
    var p = function (x) { return String(x).padStart(2, '0'); };
    return p(d.getUTCDate()) + '/' + p(d.getUTCMonth() + 1) + ' ' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes());
  }
  function cell(tr, text, cls) { var td = document.createElement('td'); td.textContent = text; if (cls) td.className = cls; tr.appendChild(td); }

  function clearOverlays() {
    overlays.forEach(function (s) { chart.removeSeries(s); }); overlays = [];
    priceLines.forEach(function (l) { candles.removePriceLine(l); }); priceLines = [];
  }
  function segment(t0, t1, price, color, width, style) {
    var s = chart.addLineSeries({ color: color, lineWidth: width, lineStyle: style, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false });
    s.setData([{ time: t0 + OFFSET, value: price }, { time: t1 + OFFSET, value: price }]);
    overlays.push(s);
  }

  function render(d) {
    var c = d.candles || [];
    candles.setData(c.map(function (x) { return { time: x.time + OFFSET, open: x.open, high: x.high, low: x.low, close: x.close }; }));
    clearOverlays();
    var lastT = c.length ? c[c.length - 1].time : 0;
    var markers = [];
    var rows = $('rows'); rows.textContent = '';

    (d.signals || []).forEach(function (s) {
      var end = s.close_time || lastT;
      var isActive = !s.close_time;
      var w = isActive ? 2 : 1, st = isActive ? 0 : 2;
      segment(s.time, end, s.entry, '#60a5fa', w, st);
      segment(s.time, end, s.target, '#22c55e', w, st);
      segment(s.time, end, s.stop, '#ef4444', w, st);
      markers.push({ time: s.time + OFFSET, position: s.side === 'BUY' ? 'belowBar' : 'aboveBar',
        color: s.side === 'BUY' ? '#22c55e' : '#ef4444', shape: s.side === 'BUY' ? 'arrowUp' : 'arrowDown',
        text: s.side === 'BUY' ? 'ទិញ' : 'លក់' });
      if (s.close_time) {
        var win = s.pnl > 0;
        markers.push({ time: s.close_time + OFFSET, position: 'inBar', color: win ? '#22c55e' : '#ef4444', shape: 'circle',
          text: 'CLOSE ' + (s.pnl > 0 ? '+' : '') + Number(s.pnl).toFixed(2) });
      }
      var tr = document.createElement('tr');
      cell(tr, hhmm(s.time));
      cell(tr, s.side === 'BUY' ? 'ទិញ' : 'លក់', s.side === 'BUY' ? 'buy' : 'sell');
      cell(tr, fmt(s.entry)); cell(tr, fmt(s.stop)); cell(tr, fmt(s.target));
      cell(tr, s.close_time ? ((s.pnl > 0 ? '✅ +' : '❌ ') + Number(s.pnl).toFixed(2)) : '⏳ កំពុងបើក', s.close_time ? (s.pnl > 0 ? 'buy' : 'sell') : '');
      rows.insertBefore(tr, rows.firstChild);
    });
    markers.sort(function (a, b) { return a.time - b.time; });
    candles.setMarkers(markers);

    var a = d.active, box = $('active'); box.textContent = '';
    if (a) {
      [['ENTRY', a.entry, 'entry', '#60a5fa'], ['TP', a.target, 'buy', '#22c55e'], ['SL', a.stop, 'sell', '#ef4444']].forEach(function (r) {
        priceLines.push(candles.createPriceLine({ price: r[1], color: r[3], lineWidth: 2, lineStyle: 0, axisLabelVisible: true, title: r[0] }));
      });
      var g = document.createElement('div'); g.className = 'grid';
      var items = [['សញ្ញាបច្ចុប្បន្ន', a.side === 'BUY' ? '🟢 ទិញ (BUY)' : '🔴 លក់ (SELL)', a.side === 'BUY' ? 'buy' : 'sell'],
                   ['តម្លៃចូល', fmt(a.entry), 'entry'], ['TP', fmt(a.target), 'buy'], ['SL', fmt(a.stop), 'sell']];
      items.forEach(function (it) {
        var card = document.createElement('div'); card.className = 'card';
        var sm = document.createElement('small'); sm.textContent = it[0];
        var b = document.createElement('b'); b.textContent = it[1]; b.className = it[2];
        card.appendChild(sm); card.appendChild(b); g.appendChild(card);
      });
      box.appendChild(g);
    } else {
      var n = document.createElement('div'); n.className = 'card'; n.textContent = '⏳ មិនមានសញ្ញាបើកនៅពេលនេះ — bot កំពុងស្កេនទីផ្សារ';
      box.appendChild(n);
    }
    if (first && c.length) {
      first = false;
      chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, c.length - 100), to: c.length + 6 });
    }
  }

  function status(d) {
    var st = $('st');
    if (d.error) { st.textContent = '⚠️ មានបញ្ហា'; st.className = 'pill bad'; }
    else { st.textContent = '● ដំណើរការ'; st.className = 'pill ok'; }
    $('mode').textContent = 'Strategy: ' + (d.strategy_mode || '-');
    $('scan').textContent = d.last_scan ? 'Scan: ' + hhmm(Math.floor(new Date(d.last_scan).getTime() / 1000)) : 'Scan: -';
  }

  function load() {
    fetch(apiUrl, { cache: 'no-store' }).then(function (r) {
      if (r.status === 401) throw new Error('unauthorized');
      return r.json();
    }).then(function (d) {
      status(d);
      if (d.candles) render(d);
    }).catch(function (e) {
      var st = $('st'); st.textContent = e.message === 'unauthorized' ? '🔒 ត្រូវការ ?key=' : '⚠️ ទាញទិន្នន័យមិនបាន'; st.className = 'pill bad';
    });
  }
  load(); setInterval(load, 30000);
})();
</script>
</body>
</html>
"""
