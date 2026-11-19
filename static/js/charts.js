/* Tiny dependency-free SVG charts for the counter dashboard (works offline). */
const CF = (() => {
  const NS = 'http://www.w3.org/2000/svg', PAL = ['#ff6b35', '#1b1f3b', '#12a37f', '#ffb703', '#8a4fd6', '#2d9cdb', '#e84a8a', '#7b82a3'];
  const fmt = n => n >= 1e5 ? (n / 1e5).toFixed(1) + 'L' : n >= 1e3 ? (n / 1e3).toFixed(n % 1e3 ? 1 : 0) + 'k' : String(Math.round(n));
  const el = (t, a = {}, p) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
  const tip = (e, text) => { el('title', {}, e).textContent = text; return e; };
  function mount(id, h) { const box = document.getElementById(id); box.innerHTML = ''; const w = box.clientWidth || 600;
    const s = el('svg', { viewBox: `0 0 ${w} ${h}`, width: '100%', height: h, role: 'img' }); box.appendChild(s); return { s, w, h }; }
  function empty(id) { document.getElementById(id).innerHTML = '<p class="mut" style="padding:40px 0;text-align:center">No data for this period yet.</p>'; }
  function legend(id, labels, vals) { const box = document.getElementById(id); const d = document.createElement('div'); d.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:8px;font-size:.84rem';
    const tot = vals.reduce((a, b) => a + b, 0) || 1; d.innerHTML = labels.map((l, i) => `<span><i style="display:inline-block;width:10px;height:10px;border-radius:3px;background:${PAL[i % PAL.length]};margin-right:5px"></i>${l} <b>${Math.round(vals[i] * 100 / tot)}%</b></span>`).join(''); box.appendChild(d); }
  function axes(c, max, left, bottom, top) { const n = 4; for (let i = 0; i <= n; i++) { const y = top + (c.h - bottom - top) * (1 - i / n);
      el('line', { x1: left, x2: c.w - 10, y1: y, y2: y, stroke: '#eef0f6' }, c.s); el('text', { x: left - 6, y: y + 4, 'text-anchor': 'end', 'font-size': 11, fill: '#6b7185' }, c.s).textContent = fmt(max * i / n); } }
  return {
    daily(id, labels, rev, ords) { if (!rev.some(v => v)) return empty(id); const c = mount(id, 280), L = 44, B = 28, T = 12, R = 10, max = Math.max(...rev) * 1.1 || 1, omax = Math.max(...ords) * 1.1 || 1;
      axes(c, max, L, B, T); const pw = (c.w - L - R) / labels.length, X = i => L + pw * (i + .5), Y = v => T + (c.h - B - T) * (1 - v / max), Yo = v => T + (c.h - B - T) * (1 - v / omax);
      ords.forEach((v, i) => tip(el('rect', { x: X(i) - pw * .3, y: Yo(v), width: pw * .6, height: c.h - B - Yo(v), fill: '#1b1f3b', opacity: .14, rx: 3 }, c.s), `${labels[i]}: ${v} orders`));
      const pts = rev.map((v, i) => `${X(i)},${Y(v)}`); el('polygon', { points: `${X(0)},${c.h - B} ${pts.join(' ')} ${X(rev.length - 1)},${c.h - B}`, fill: 'rgba(255,107,53,.14)' }, c.s);
      el('polyline', { points: pts.join(' '), fill: 'none', stroke: '#ff6b35', 'stroke-width': 2.5, 'stroke-linejoin': 'round' }, c.s);
      rev.forEach((v, i) => tip(el('circle', { cx: X(i), cy: Y(v), r: labels.length > 40 ? 2 : 3.5, fill: '#fff', stroke: '#ff6b35', 'stroke-width': 2 }, c.s), `${labels[i]}: Rs ${v.toLocaleString('en-IN')}`));
      const step = Math.ceil(labels.length / 8); labels.forEach((l, i) => { if (i % step === 0) el('text', { x: X(i), y: c.h - 8, 'text-anchor': 'middle', 'font-size': 11, fill: '#6b7185' }, c.s).textContent = l; });
      const g = document.getElementById(id), d = document.createElement('div'); d.style.cssText = 'font-size:.84rem;margin-top:4px'; d.innerHTML = '<span style="color:#ff6b35">&#9632;</span> Revenue (Rs) &nbsp; <span style="color:#b9bbc8">&#9632;</span> Orders'; g.appendChild(d); },
    bars(id, labels, vals, color) { if (!vals.some(v => v)) return empty(id); const c = mount(id, 250), L = 38, B = 26, T = 12, max = Math.max(...vals) * 1.15 || 1; axes(c, max, L, B, T);
      const pw = (c.w - L - 10) / labels.length; vals.forEach((v, i) => { const h = (c.h - B - T) * v / max; tip(el('rect', { x: L + pw * i + pw * .15, y: c.h - B - h, width: pw * .7, height: h, fill: color, rx: 4 }, c.s), `${labels[i]}: ${v}`);
        el('text', { x: L + pw * (i + .5), y: c.h - 8, 'text-anchor': 'middle', 'font-size': 11, fill: '#6b7185' }, c.s).textContent = labels[i]; }); },
    hbars(id, labels, vals, color) { if (!vals.some(v => v)) return empty(id); const rowH = 30, c = mount(id, labels.length * rowH + 10), max = Math.max(...vals) || 1, L = 130;
      labels.forEach((l, i) => { const y = 6 + i * rowH, w = (c.w - L - 40) * vals[i] / max; el('text', { x: L - 8, y: y + 17, 'text-anchor': 'end', 'font-size': 12, fill: '#1b1f3b' }, c.s).textContent = l.length > 18 ? l.slice(0, 17) + '…' : l;
        tip(el('rect', { x: L, y: y + 3, width: Math.max(w, 2), height: 18, fill: color, rx: 5 }, c.s), `${l}: ${vals[i]}`); el('text', { x: L + w + 6, y: y + 17, 'font-size': 12, fill: '#6b7185' }, c.s).textContent = vals[i]; }); },
    donut(id, labels, vals, money) { if (!vals.some(v => v)) return empty(id); const c = mount(id, 190), cx = c.w / 2, cy = 95, R = 80, r = 50, tot = vals.reduce((a, b) => a + b, 0); let a0 = -Math.PI / 2;
      vals.forEach((v, i) => { const a1 = a0 + 2 * Math.PI * v / tot, big = a1 - a0 > Math.PI ? 1 : 0, P = (rad, a) => `${cx + rad * Math.cos(a)},${cy + rad * Math.sin(a)}`;
        const d = vals.length === 1 ? `M${cx - R},${cy} a${R},${R} 0 1,0 ${2 * R},0 a${R},${R} 0 1,0 ${-2 * R},0 M${cx - r},${cy} a${r},${r} 0 1,1 ${2 * r},0 a${r},${r} 0 1,1 ${-2 * r},0` : `M${P(R, a0)} A${R},${R} 0 ${big} 1 ${P(R, a1 - .001)} L${P(r, a1 - .001)} A${r},${r} 0 ${big} 0 ${P(r, a0)} Z`;
        tip(el('path', { d, fill: PAL[i % PAL.length], 'fill-rule': 'evenodd', stroke: '#fff', 'stroke-width': 2 }, c.s), `${labels[i]}: ${money ? 'Rs ' + v.toLocaleString('en-IN') : v}`); a0 = a1; });
      el('text', { x: cx, y: cy + 6, 'text-anchor': 'middle', 'font-size': 18, 'font-weight': 800, fill: '#1b1f3b' }, c.s).textContent = money ? 'Rs ' + fmt(tot) : tot; legend(id, labels, vals); }
  };
})();
