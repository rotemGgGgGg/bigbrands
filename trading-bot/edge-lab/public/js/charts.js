// Hand-built SVG charts: equity/drawdown lines, Monte Carlo fan with ending distribution, bars, histograms, heatmap.
// Every chart re-renders on resize and shows a tooltip on hover. Colours come from the design tokens.
import { esc, fmt } from "./util.js";

const C = { fg: "#f5f5f5", fg2: "#888888", muted: "#555555", grid: "#161616", line: "#e8e8e8", red: "#e74747", red2: "#a92e35" };
const NS = "http://www.w3.org/2000/svg";
const ro = new ResizeObserver((entries) => { for (const e of entries) { const el = e.target; if (el._w !== Math.round(e.contentRect.width) && el._render) { el._w = Math.round(e.contentRect.width); el._render(); } } });

function mount(el, render) { el.classList.add("chart"); el._render = render; el._w = Math.round(el.clientWidth); render(); ro.observe(el); }

function niceTicks(lo, hi, n = 4) {
  if (lo === hi) { lo -= 1; hi += 1; }
  const span = hi - lo, step0 = span / n, mag = 10 ** Math.floor(Math.log10(step0)), err = step0 / mag;
  const step = (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1) * mag;
  const out = []; for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(10));
  return out;
}

/** Fritsch–Carlson monotone cubic through points (works for either x direction). */
export function smoothPath(pts, move = true) {
  const n = pts.length; if (n < 2) return "";
  if (n === 2) return `${move ? "M" : "L"}${pts[0][0]},${pts[0][1]}L${pts[1][0]},${pts[1][1]}`;
  const dx = [], dy = [], m = [], t = [];
  for (let i = 0; i < n - 1; i++) { dx[i] = pts[i + 1][0] - pts[i][0]; dy[i] = pts[i + 1][1] - pts[i][1]; m[i] = dx[i] ? dy[i] / dx[i] : 0; }
  t[0] = m[0]; t[n - 1] = m[n - 2];
  for (let i = 1; i < n - 1; i++) t[i] = m[i - 1] * m[i] <= 0 ? 0 : (m[i - 1] + m[i]) / 2;
  for (let i = 0; i < n - 1; i++) {
    if (m[i] === 0) { t[i] = 0; t[i + 1] = 0; continue; }
    const a = t[i] / m[i], b = t[i + 1] / m[i], s = a * a + b * b;
    if (s > 9) { const k = 3 / Math.sqrt(s); t[i] = k * a * m[i]; t[i + 1] = k * b * m[i]; }
  }
  let d = `${move ? "M" : "L"}${pts[0][0].toFixed(2)},${pts[0][1].toFixed(2)}`;
  for (let i = 0; i < n - 1; i++) {
    const h = dx[i] / 3;
    d += `C${(pts[i][0] + h).toFixed(2)},${(pts[i][1] + t[i] * h).toFixed(2)} ${(pts[i + 1][0] - h).toFixed(2)},${(pts[i + 1][1] - t[i + 1] * h).toFixed(2)} ${pts[i + 1][0].toFixed(2)},${pts[i + 1][1].toFixed(2)}`;
  }
  return d;
}

function tooltip(el) {
  let t = el.querySelector(".tooltip");
  if (!t) { t = document.createElement("div"); t.className = "tooltip"; el.append(t); }
  return {
    show(x, y, inner) {
      t.innerHTML = inner; t.classList.add("on");
      const w = el.clientWidth, tw = t.offsetWidth;
      let left = x + 14; if (left + tw > w) left = x - tw - 14;
      t.style.left = `${Math.max(0, left)}px`;
      t.style.top = `${Math.max(y - 10, 0)}px`;
    },
    hide() { t.classList.remove("on"); },
  };
}

const toTime = (x) => (typeof x === "number" ? x : Date.parse(x));

/**
 * Line chart over time.
 * opts.series: [{ name, points: [[date, y]], color, width, fill, fillOpacity, dash }]
 * opts.shadeFrom: ISO date — shades the out-of-sample region. opts.yFmt / opts.tipFmt format values.
 */
export function lineChart(el, opts) {
  const { height = 240, series, shadeFrom, yFmt = (v) => fmt.n(v, Math.abs(v) < 10 ? 1 : 0), tipFmt = (v) => fmt.r(v, 2), zero = true, animate = true, area = true } = opts;
  let first = true;
  mount(el, () => {
    const W = Math.max(el.clientWidth, 280), H = height, L = 46, R = 14, T = 10, B = 24;
    const all = series.flatMap((s) => s.points);
    if (!all.length) { el.innerHTML = `<div class="caption" style="padding:40px 0;text-align:center">No data</div>`; return; }
    const xs = all.map((p) => toTime(p[0])), ys = all.map((p) => p[1]);
    let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys, zero ? 0 : Infinity), y1 = Math.max(...ys, zero ? 0 : -Infinity);
    const pad = (y1 - y0) * 0.06 || 1; y0 -= pad; y1 += pad;
    const ticks = niceTicks(y0, y1, H < 150 ? 2 : 4); y0 = Math.min(y0, ticks[0]); y1 = Math.max(y1, ticks.at(-1));
    const X = (t) => L + ((t - x0) / (x1 - x0 || 1)) * (W - L - R), Y = (v) => T + ((y1 - v) / (y1 - y0 || 1)) * (H - T - B);
    let g = `<svg viewBox="0 0 ${W} ${H}" height="${H}" role="img" aria-label="${esc(opts.label || "Line chart")}">`;
    if (shadeFrom && toTime(shadeFrom) < x1 && toTime(shadeFrom) > x0) {
      const sx = X(toTime(shadeFrom));
      g += `<rect x="${sx}" y="${T}" width="${W - R - sx}" height="${H - T - B}" fill="#ffffff" opacity=".022"/><line x1="${sx}" x2="${sx}" y1="${T}" y2="${H - B}" stroke="#262626" stroke-dasharray="2 3"/>`;
      g += `<text x="${sx + 6}" y="${T + 11}" style="fill:#4a4a4a">out-of-sample</text>`;
    }
    for (const v of ticks) g += `<line class="${v === 0 ? "zero" : "grid-line"}" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 8}" y="${Y(v) + 3}" text-anchor="end">${esc(yFmt(v))}</text>`;
    const yr0 = new Date(x0).getFullYear(), yr1 = new Date(x1).getFullYear(), every = Math.max(1, Math.ceil((yr1 - yr0 + 1) / Math.max(2, Math.floor((W - L - R) / 70))));
    for (let y = yr0 + 1; y <= yr1; y++) if ((y - yr0) % every === 0) { const tx = X(Date.UTC(y, 0, 1)); if (tx > L + 10 && tx < W - R - 10) g += `<text x="${tx}" y="${H - 6}" text-anchor="middle">${y}</text>`; }
    series.forEach((s, si) => {
      const pts = s.points.map((p) => [X(toTime(p[0])), Y(p[1])]);
      const d = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join("");
      if (area && s.fill !== false) {
        const gid = `g${Math.random().toString(36).slice(2, 8)}`, base = Y(Math.max(y0, Math.min(0, y1)));
        g += `<defs><linearGradient id="${gid}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${s.fillColor || s.color || C.line}" stop-opacity="${s.fillOpacity ?? 0.1}"/><stop offset="1" stop-color="${s.fillColor || s.color || C.line}" stop-opacity="0"/></linearGradient></defs>`;
        g += `<path class="appear" d="${d}L${pts.at(-1)[0]},${base}L${pts[0][0]},${base}Z" fill="url(#${gid})"/>`;
      }
      g += `<path class="${animate && first ? "draw" : ""}" data-s="${si}" d="${d}" fill="none" stroke="${s.color || C.line}" stroke-width="${s.width || 1.5}" ${s.dash ? `stroke-dasharray="${s.dash}"` : ""} stroke-linejoin="round" stroke-linecap="round" opacity="${s.opacity ?? 1}"/>`;
      if (s.endDot !== false && si === 0) g += `<circle cx="${pts.at(-1)[0]}" cy="${pts.at(-1)[1]}" r="2.6" fill="${s.color || C.line}"/>`;
    });
    g += `<line class="guide" x1="0" x2="0" y1="${T}" y2="${H - B}" visibility="hidden"/><g class="dots"></g><rect class="hit" x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent"/></svg>`;
    el.innerHTML = g;
    el.querySelectorAll("path.draw").forEach((p) => p.style.setProperty("--len", Math.ceil(p.getTotalLength())));
    first = false;
    const tip = tooltip(el), guide = el.querySelector(".guide"), dots = el.querySelector(".dots"), hit = el.querySelector(".hit");
    const base = series[0].points;
    hit.addEventListener("mousemove", (ev) => {
      const r = el.getBoundingClientRect(), mx = ((ev.clientX - r.left) / r.width) * W;
      const t = x0 + ((mx - L) / (W - L - R)) * (x1 - x0);
      let lo = 0, hi = base.length - 1; while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (toTime(base[mid][0]) < t) lo = mid; else hi = mid; }
      const i = Math.abs(toTime(base[lo][0]) - t) < Math.abs(toTime(base[hi][0]) - t) ? lo : hi, px = X(toTime(base[i][0]));
      guide.setAttribute("x1", px); guide.setAttribute("x2", px); guide.setAttribute("visibility", "visible");
      let rows = "", dd = "";
      series.forEach((s) => {
        const p = s.points.reduce((best, q) => (Math.abs(toTime(q[0]) - toTime(base[i][0])) < Math.abs(toTime(best[0]) - toTime(base[i][0])) ? q : best), s.points[0]);
        dd += `<circle cx="${X(toTime(p[0]))}" cy="${Y(p[1])}" r="3.2" fill="#050505" stroke="${s.color || C.line}" stroke-width="1.5"/>`;
        rows += `<div class="t-row"><span>${esc(s.name || "Value")}</span><span>${esc(tipFmt(p[1]))}</span></div>`;
      });
      dots.innerHTML = dd;
      tip.show((px / W) * r.width, ((Y(base[i][1]) / H) * r.height), `<div class="t-head">${esc(typeof base[i][0] === "string" ? fmt.date(base[i][0]) : base[i][0])}</div>${rows}`);
    });
    hit.addEventListener("mouseleave", () => { guide.setAttribute("visibility", "hidden"); dots.innerHTML = ""; tip.hide(); });
  });
}

/** Monte Carlo fan: percentile bands, median path, start capital, ruin line, ending distribution on the right. */
export function fanChart(el, mc, opts = {}) {
  const { height = 380, yFmt = fmt.usdShort, ruinLevel = null, start = null, xLabel = "trades" } = opts;
  let first = true;
  mount(el, () => {
    const W = Math.max(el.clientWidth, 320), H = height, L = 56, HIST = W > 560 ? 96 : 0, R = 16 + HIST, T = 16, B = 28;
    const fan = mc.fan, steps = fan.map((f) => f.step), last = steps.at(-1);
    const ends = mc.ending;
    let lo = Math.min(...fan.map((f) => f.q[0]), ruinLevel ?? Infinity, start ?? Infinity), hi = Math.max(...fan.map((f) => f.q[4]), start ?? -Infinity);
    const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
    const ticks = niceTicks(lo, hi, 5); lo = Math.min(lo, ticks[0]); hi = Math.max(hi, ticks.at(-1));
    const X = (s) => L + (s / (last || 1)) * (W - L - R), Y = (v) => T + ((hi - v) / (hi - lo || 1)) * (H - T - B);
    const path = (k) => fan.map((f) => [X(f.step), Y(f.q[k])]);
    const band = (a, b) => `${smoothPath(path(b))}${smoothPath(path(a).reverse(), false)}Z`;
    let g = `<svg viewBox="0 0 ${W} ${H}" height="${H}" role="img" aria-label="Monte Carlo fan chart">`;
    for (const v of ticks) g += `<line class="grid-line" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 10}" y="${Y(v) + 3}" text-anchor="end">${esc(yFmt(v))}</text>`;
    for (const f of [0, 0.25, 0.5, 0.75, 1]) { const s = Math.round(last * f); g += `<text x="${X(s)}" y="${H - 8}" text-anchor="${f === 0 ? "start" : f === 1 ? "end" : "middle"}">${f === 0 ? "0" : fmt.n(s)}${f === 1 ? ` ${xLabel}` : ""}</text>`; }
    g += `<defs><clipPath id="fanclip"><rect x="${L}" y="${T}" width="${W - L - 16}" height="${H - T - B}"/></clipPath></defs><g clip-path="url(#fanclip)">`;
    g += `<path class="appear" d="${band(0, 4)}" fill="#ffffff" fill-opacity=".05"/>`;
    g += `<path class="appear" d="${band(1, 3)}" fill="#ffffff" fill-opacity=".075"/>`;
    g += `<path d="${smoothPath(path(0))}" fill="none" stroke="#5a5a5a" stroke-width="1" stroke-dasharray="3 4"/>`;
    g += `<path d="${smoothPath(path(4))}" fill="none" stroke="#5a5a5a" stroke-width="1" stroke-dasharray="3 4"/>`;
    g += `<path d="${smoothPath(path(1))}" fill="none" stroke="#3a3a3a" stroke-width="1"/><path d="${smoothPath(path(3))}" fill="none" stroke="#3a3a3a" stroke-width="1"/>`;
    if (start != null) g += `<line x1="${L}" x2="${W - R}" y1="${Y(start)}" y2="${Y(start)}" stroke="#3d3d3d" stroke-dasharray="1 3"/><text x="${W - R - 8}" y="${Y(start) + 13}" text-anchor="end" style="fill:#6a6a6a">start ${esc(yFmt(start))}</text>`;
    if (ruinLevel != null && ruinLevel > lo) g += `<line x1="${L}" x2="${W - R}" y1="${Y(ruinLevel)}" y2="${Y(ruinLevel)}" stroke="${C.red}" stroke-opacity=".55" stroke-dasharray="4 4"/><text x="${W - R - 8}" y="${Y(ruinLevel) - 6}" text-anchor="end" style="fill:${C.red};opacity:.8">ruin ${esc(yFmt(ruinLevel))}</text>`;
    g += `<path class="${first ? "draw" : ""}" d="${smoothPath(path(2))}" fill="none" stroke="${C.fg}" stroke-width="1.8" stroke-linecap="round"/>`;
    g += `</g>`;
    const e = fan.at(-1);
    [[4, "95th"], [3, "75th"], [2, "Median"], [1, "25th"], [0, "5th"]].forEach(([k, lab], j) => {
      g += `<circle cx="${X(last)}" cy="${Y(e.q[k])}" r="${k === 2 ? 3 : 2}" fill="${k === 2 ? C.fg : "#6a6a6a"}"/>`;
    });
    // ending distribution
    if (HIST && ends?.counts?.length) {
      const mx = Math.max(...ends.counts), hx = W - HIST + 8;
      g += `<line x1="${hx - 4}" x2="${hx - 4}" y1="${T}" y2="${H - B}" stroke="#1c1c1c"/>`;
      ends.counts.forEach((c, i) => {
        const yA = Y(ends.edges[i + 1]), yB = Y(ends.edges[i]), w = (c / mx) * (HIST - 22);
        const below = ruinLevel != null && ends.edges[i + 1] <= ruinLevel, under = start != null && ends.edges[i + 1] <= start;
        const top = Math.max(Math.min(yA, yB), T), bot = Math.min(Math.max(yA, yB), H - B);
        if (bot - top < 0.5 || !c) return;
        g += `<rect class="appear" x="${hx}" y="${top + 0.5}" width="${Math.max(w, 1)}" height="${Math.max(bot - top - 1, 0.5)}" rx="1" fill="${below ? C.red : under ? "#8a4a4d" : "#d9d9d9"}" fill-opacity="${below ? 0.8 : under ? 0.6 : 0.42}"/>`;
      });
      g += `<text x="${hx}" y="${T - 4}" style="fill:#4a4a4a">ending</text>`;
      [[4, "95"], [2, "50"], [0, "5"]].forEach(([k, lab]) => { g += `<text x="${W - 4}" y="${Y(e.q[k]) + 3}" text-anchor="end" style="fill:${k === 2 ? C.fg : "#6a6a6a"}">p${lab}</text>`; });
    }
    g += `<line class="guide" x1="0" x2="0" y1="${T}" y2="${H - B}" visibility="hidden"/><g class="dots"></g><rect class="hit" x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent"/></svg>`;
    el.innerHTML = g;
    el.querySelectorAll("path.draw").forEach((p) => p.style.setProperty("--len", Math.ceil(p.getTotalLength())));
    first = false;
    const tip = tooltip(el), guide = el.querySelector(".guide"), dots = el.querySelector(".dots");
    el.querySelector(".hit").addEventListener("mousemove", (ev) => {
      const r = el.getBoundingClientRect(), mx = ((ev.clientX - r.left) / r.width) * W, s = ((mx - L) / (W - L - R)) * last;
      const f = fan.reduce((b, x) => (Math.abs(x.step - s) < Math.abs(b.step - s) ? x : b), fan[0]), px = X(f.step);
      guide.setAttribute("x1", px); guide.setAttribute("x2", px); guide.setAttribute("visibility", "visible");
      dots.innerHTML = f.q.map((v, k) => `<circle cx="${px}" cy="${Y(v)}" r="${k === 2 ? 3.4 : 2.4}" fill="#050505" stroke="${k === 2 ? C.fg : "#777"}" stroke-width="1.4"/>`).join("");
      const lab = ["5th", "25th", "Median", "75th", "95th"];
      tip.show((px / W) * r.width, (Y(f.q[2]) / H) * r.height, `<div class="t-head">after ${fmt.n(f.step)} ${esc(xLabel)}</div>${[4, 3, 2, 1, 0].map((k) => `<div class="t-row"><span>${lab[k]}</span><span>${esc(yFmt(f.q[k]))}</span></div>`).join("")}`);
    });
    el.querySelector(".hit").addEventListener("mouseleave", () => { guide.setAttribute("visibility", "hidden"); dots.innerHTML = ""; tip.hide(); });
  });
}

/** Vertical bars (e.g. R by year). items: [{ label, value, sub }] */
export function barChart(el, items, opts = {}) {
  const { height = 170, tipFmt = (v) => fmt.rr(v, 1) } = opts;
  mount(el, () => {
    const W = Math.max(el.clientWidth, 280), H = height, L = 40, R = 8, T = 14, B = 22;
    const vals = items.map((i) => i.value); let lo = Math.min(0, ...vals), hi = Math.max(0, ...vals);
    const ticks = niceTicks(lo, hi, 3); lo = Math.min(lo, ticks[0]); hi = Math.max(hi, ticks.at(-1));
    const Y = (v) => T + ((hi - v) / (hi - lo || 1)) * (H - T - B), bw = (W - L - R) / items.length;
    let g = `<svg viewBox="0 0 ${W} ${H}" height="${H}" role="img" aria-label="Bar chart">`;
    for (const v of ticks) g += `<line class="${v === 0 ? "zero" : "grid-line"}" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 8}" y="${Y(v) + 3}" text-anchor="end">${fmt.n(v)}</text>`;
    items.forEach((it, i) => {
      const x = L + i * bw + bw * 0.22, w = bw * 0.56, y = Y(Math.max(it.value, 0)), h = Math.max(Math.abs(Y(it.value) - Y(0)), 1);
      g += `<rect class="bar appear" data-i="${i}" x="${x}" y="${y}" width="${w}" height="${h}" rx="2" fill="${it.value >= 0 ? "#d9d9d9" : C.red2}" fill-opacity="${it.value >= 0 ? 0.82 : 0.9}" style="animation-delay:${i * 25}ms"/>`;
      if (items.length <= 20 || i % 2 === 0) g += `<text x="${x + w / 2}" y="${H - 6}" text-anchor="middle">${esc(it.label)}</text>`;
    });
    g += `</svg>`; el.innerHTML = g;
    const tip = tooltip(el);
    el.querySelectorAll("rect.bar").forEach((r) => {
      r.addEventListener("mouseenter", () => { const it = items[+r.dataset.i], b = el.getBoundingClientRect(), rb = r.getBoundingClientRect(); r.setAttribute("fill-opacity", 1); tip.show(rb.left - b.left + rb.width / 2, rb.top - b.top, `<div class="t-head">${esc(it.label)}</div><div class="t-row"><span>Total</span><span>${esc(tipFmt(it.value))}</span></div>${it.sub ? `<div class="t-row"><span>Trades</span><span>${esc(it.sub)}</span></div>` : ""}`); });
      r.addEventListener("mouseleave", () => { r.setAttribute("fill-opacity", items[+r.dataset.i].value >= 0 ? 0.82 : 0.9); tip.hide(); });
    });
  });
}

/** Histogram of a distribution. hist: { edges, counts } */
export function histChart(el, hist, opts = {}) {
  const { height = 170, xFmt = (v) => fmt.r(v, 1), marker = 0 } = opts;
  mount(el, () => {
    const W = Math.max(el.clientWidth, 260), H = height, L = 10, R = 10, T = 10, B = 22;
    const { edges, counts } = hist; if (!counts?.length) { el.innerHTML = ""; return; }
    const mx = Math.max(...counts), x0 = edges[0], x1 = edges.at(-1), X = (v) => L + ((v - x0) / (x1 - x0)) * (W - L - R), Y = (c) => T + (1 - c / mx) * (H - T - B);
    let g = `<svg viewBox="0 0 ${W} ${H}" height="${H}" role="img" aria-label="Histogram">`;
    counts.forEach((c, i) => { const a = X(edges[i]), b = X(edges[i + 1]); g += `<rect class="appear" x="${a + 0.5}" y="${Y(c)}" width="${Math.max(b - a - 1, 0.5)}" height="${H - B - Y(c)}" rx="1" fill="${edges[i + 1] <= marker ? C.red2 : "#d9d9d9"}" fill-opacity="${edges[i + 1] <= marker ? 0.85 : 0.7}"/>`; });
    if (marker > x0 && marker < x1) g += `<line x1="${X(marker)}" x2="${X(marker)}" y1="${T}" y2="${H - B}" stroke="#3a3a3a" stroke-dasharray="2 3"/>`;
    [x0, (x0 + x1) / 2, x1].forEach((v, i) => { g += `<text x="${X(v)}" y="${H - 6}" text-anchor="${["start", "middle", "end"][i]}">${esc(xFmt(v))}</text>`; });
    el.innerHTML = g + "</svg>";
  });
}

/** Correlation matrix as an HTML grid (grey for positive, red for negative). */
export function heatmap(el, labels, matrix) {
  const n = labels.length;
  const cell = (v, i, j) => {
    const a = Math.min(Math.abs(v), 1), bg = i === j ? "#1a1a1a" : v >= 0 ? `rgba(217,217,217,${0.05 + a * 0.55})` : `rgba(231,71,71,${0.08 + a * 0.6})`;
    return `<div class="c" style="background:${bg};color:${a > 0.55 && v >= 0 && i !== j ? "#0a0a0a" : "#d0d0d0"}" title="${esc(labels[i])} × ${esc(labels[j])}: ${v.toFixed(2)}">${i === j ? "1" : v.toFixed(2)}</div>`;
  };
  el.innerHTML = `<div class="heat" style="grid-template-columns: 110px repeat(${n}, minmax(34px, 1fr))"><div></div>${labels.map((l) => `<div class="lab top" title="${esc(l)}">${esc(l.slice(0, 10))}</div>`).join("")}${matrix.map((row, i) => `<div class="lab" title="${esc(labels[i])}">${esc(labels[i])}</div>${row.map((v, j) => cell(v, i, j)).join("")}`).join("")}</div>`;
}

export function sparkline(values, w = 96, h = 26, color = "#d9d9d9") {
  if (!values?.length) return "";
  const lo = Math.min(0, ...values), hi = Math.max(0, ...values), span = hi - lo || 1;
  const pts = values.map((v, i) => `${((i / (values.length - 1)) * w).toFixed(1)},${(h - 2 - ((v - lo) / span) * (h - 4)).toFixed(1)}`).join(" ");
  const z = h - 2 - ((0 - lo) / span) * (h - 4), endUp = values.at(-1) >= 0;
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><line x1="0" x2="${w}" y1="${z}" y2="${z}" stroke="#262626" stroke-dasharray="2 2"/><polyline points="${pts}" fill="none" stroke="${endUp ? color : C.red}" stroke-width="1.3" stroke-linejoin="round"/></svg>`;
}
