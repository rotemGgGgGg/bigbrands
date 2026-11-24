// DOM, formatting and markdown helpers.
export const $ = (s, el = document) => el.querySelector(s);
export const $$ = (s, el = document) => [...el.querySelectorAll(s)];
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export function html(strings, ...vals) {
  return strings.reduce((out, s, i) => out + s + (i < vals.length ? (Array.isArray(vals[i]) ? vals[i].join("") : vals[i] ?? "") : ""), "");
}

export const fmt = {
  r: (x, d = 2) => (x == null || !Number.isFinite(x) ? "—" : `${x > 0 ? "+" : x < 0 ? "−" : ""}${Math.abs(x).toFixed(d)}`),
  rr: (x, d = 2) => (x == null || !Number.isFinite(x) ? "—" : `${fmt.r(x, d)}R`),
  n: (x, d = 0) => (x == null || !Number.isFinite(x) ? "—" : x.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d })),
  pct: (x, d = 1) => (x == null || !Number.isFinite(x) ? "—" : `${x.toFixed(d)}%`),
  usd: (x) => (x == null || !Number.isFinite(x) ? "—" : `${x < 0 ? "−" : ""}$${Math.abs(x).toLocaleString("en-US", { maximumFractionDigits: 0 })}`),
  usdShort: (x) => {
    if (x == null || !Number.isFinite(x)) return "—";
    const a = Math.abs(x), s = x < 0 ? "−" : "";
    return a >= 1e6 ? `${s}$${(a / 1e6).toFixed(2)}M` : a >= 1e3 ? `${s}$${(a / 1e3).toFixed(a >= 1e5 ? 0 : 1)}k` : `${s}$${a.toFixed(0)}`;
  },
  t: (x) => (x == null || !Number.isFinite(x) ? "—" : x.toFixed(2)),
  date: (s) => (s ? new Date(s).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "—"),
  time: (s) => (s ? new Date(s).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) : ""),
  ago(s) {
    const d = (Date.now() - new Date(s).getTime()) / 1000;
    if (d < 60) return "just now"; if (d < 3600) return `${Math.floor(d / 60)}m ago`; if (d < 86400) return `${Math.floor(d / 3600)}h ago`;
    if (d < 86400 * 30) return `${Math.floor(d / 86400)}d ago`; return fmt.date(s);
  },
};
export const signCls = (x) => (x == null ? "" : x > 0 ? "pos" : x < 0 ? "neg" : "");

export function toast(msg, kind = "") {
  const el = document.createElement("div"); el.className = `toast ${kind}`; el.textContent = msg;
  document.getElementById("toasts").append(el);
  setTimeout(() => { el.style.transition = "opacity .3s"; el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, 3800);
}

export const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

/** Minimal, safe markdown: everything is escaped first, then a small set of constructs is restored. */
export function markdown(src) {
  const blocks = [];
  let s = String(src ?? "").replace(/\r/g, "");
  s = s.replace(/```(\w*)\n?([\s\S]*?)(```|$)/g, (_, lang, code) => { blocks.push(`<pre><code>${esc(code.replace(/\n$/, ""))}</code></pre>`); return `\u0000${blocks.length - 1}\u0000`; });
  const inline = (t) => esc(t)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  const lines = s.split("\n"), out = [];
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    const ph = l.match(/^\u0000(\d+)\u0000$/);
    if (ph) { out.push(blocks[+ph[1]]); continue; }
    if (/^\s*\|.*\|\s*$/.test(l) && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1] || "")) {
      const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const head = cells(l); i += 1; const rows = [];
      while (i + 1 < lines.length && /^\s*\|.*\|\s*$/.test(lines[i + 1])) { i++; rows.push(cells(lines[i])); }
      out.push(`<table><thead><tr>${head.map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
      continue;
    }
    const h = l.match(/^(#{1,4})\s+(.*)/);
    if (h) { out.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`); continue; }
    if (/^\s*[-*]\s+/.test(l)) { const items = []; while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*[-*]\s+/, "")); i--; out.push(`<ul>${items.map((x) => `<li>${inline(x)}</li>`).join("")}</ul>`); continue; }
    if (/^\s*\d+[.)]\s+/.test(l)) { const items = []; while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*\d+[.)]\s+/, "")); i--; out.push(`<ol>${items.map((x) => `<li>${inline(x)}</li>`).join("")}</ol>`); continue; }
    if (/^>\s?/.test(l)) { out.push(`<blockquote>${inline(l.replace(/^>\s?/, ""))}</blockquote>`); continue; }
    if (!l.trim()) { out.push(""); continue; }
    const para = [l]; while (i + 1 < lines.length && lines[i + 1].trim() && !/^(#{1,4}\s|\s*[-*]\s|\s*\d+[.)]\s|>|\u0000|\s*\|)/.test(lines[i + 1])) para.push(lines[++i]);
    out.push(`<p>${para.map(inline).join("<br>")}</p>`);
  }
  return out.join("\n");
}

export function emptyState(icon, title, text, action = "") {
  return `<div class="empty"><div class="ring">${icon}</div><h3>${esc(title)}</h3><p>${esc(text)}</p>${action}</div>`;
}

export function skeleton(rows = [64, 280, 200]) {
  return `<div class="loading-page">${rows.map((h) => `<div class="skeleton" style="height:${h}px"></div>`).join("")}</div>`;
}

export function errorBox(title, msg) { return `<div class="err-box"><b>${esc(title)}</b><div>${esc(msg)}</div></div>`; }
