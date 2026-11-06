# Frosted glass look — exact recipe

Hand this whole file to the AI. It is the exact code behind the look: copy it, do not "reinterpret" it.

## Why other attempts fail (read first)

1. **The background is the effect.** Frosted glass is only visible when there is something soft and uneven *behind* it. A flat grey or white page makes `backdrop-filter` do nothing, so the panels look like plain white boxes. The waves below are what the glass blurs.
2. **The waves are an inline SVG, not an image or a CSS gradient.** Thick curved strokes (stroke-width 160–190) with a light-to-grey gradient, each with a blurred darker copy under it as a shadow. That fake 3D shading is what makes it look like the sculpted reference.
3. **The blur filters need `filterUnits="userSpaceOnUse"` and a huge region** (x/y -400, width/height 1800). With the default filter region the blur gets clipped and you see hard horizontal bands across the screen.
4. **Panels are barely white:** `rgba(255,255,255,.34)` with `backdrop-filter: blur(30px) saturate(140%)`, a 1px border `rgba(255,255,255,.6)`, a 1px white inset highlight on top, and a soft long shadow. More opaque than ~.5 and it stops looking like glass.
5. **Nothing behind the panels may have an opaque background.** Main area, sidebar and right column must be transparent or translucent, otherwise they cover the waves.
6. **Only one accent colour** (`#3a6ff0`, quiet blue). Everything else is cool grey. Green/red only for profit/loss.
7. **The selected item is a brighter raised pill** (`rgba(255,255,255,.78)` plus a small shadow), not a coloured background.
8. **`backdrop-filter` needs `-webkit-backdrop-filter` too** for Safari/iPhone.

## Step 1 — put this right after `<body>`

```html
<div class="frost-bg" aria-hidden="true"><svg viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice">
  <defs>
    <linearGradient id="fb" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#eef0f4"/><stop offset="1" stop-color="#d7dbe2"/></linearGradient>
    <linearGradient id="r1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".55" stop-color="#e6e9ee"/><stop offset="1" stop-color="#bfc5cf"/></linearGradient>
    <linearGradient id="r2" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f7f8fa"/><stop offset=".6" stop-color="#d9dde4"/><stop offset="1" stop-color="#b8bfca"/></linearGradient>
    <filter id="soft" filterUnits="userSpaceOnUse" x="-400" y="-400" width="1800" height="1800"><feGaussianBlur stdDeviation="5"/></filter>
    <filter id="shade" filterUnits="userSpaceOnUse" x="-400" y="-400" width="1800" height="1800"><feGaussianBlur stdDeviation="22"/></filter>
  </defs>
  <rect width="1000" height="1000" fill="url(#fb)"/>
  <g fill="none" stroke-linecap="round">
    <path d="M-120 210 C 120 60, 260 360, 470 230 S 820 40, 1120 220" stroke="#9aa3b2" stroke-opacity=".5" stroke-width="170" filter="url(#shade)" transform="translate(0 40)"/>
    <path d="M-120 210 C 120 60, 260 360, 470 230 S 820 40, 1120 220" stroke="url(#r1)" stroke-width="160" filter="url(#soft)"/>
    <path d="M-160 520 C 90 380, 330 700, 560 520 S 900 330, 1160 560" stroke="#8f99a9" stroke-opacity=".48" stroke-width="190" filter="url(#shade)" transform="translate(0 46)"/>
    <path d="M-160 520 C 90 380, 330 700, 560 520 S 900 330, 1160 560" stroke="url(#r2)" stroke-width="180" filter="url(#soft)"/>
    <path d="M-140 860 C 140 720, 380 1010, 620 850 S 960 700, 1180 880" stroke="#8f99a9" stroke-opacity=".46" stroke-width="180" filter="url(#shade)" transform="translate(0 44)"/>
    <path d="M-140 860 C 140 720, 380 1010, 620 850 S 960 700, 1180 880" stroke="url(#r1)" stroke-width="170" filter="url(#soft)"/>
    <path d="M300 -80 C 380 120, 240 300, 360 480" stroke="#ffffff" stroke-opacity=".55" stroke-width="60" filter="url(#shade)"/>
  </g>
</svg></div>
```

It stays fixed behind everything (`z-index: -2`), so it never scrolls and never blocks clicks.

## Step 2 — the CSS

This is the exact CSS used. Selectors such as `.stat`, `.chart-card`, `.table`, `.side`, `.right` are the class names of *this* app; map them to your own cards and columns. If the app has no dark mode, drop every `:root:not([data-theme="night"])` prefix.

```css
/* =====================================================================
   FROST — the light theme, now the default. Frosted panes floating over a
   soft sculpted grey; cool greys with one quiet blue. The dark theme above
   is untouched and still on the switch.
   ===================================================================== */
.frost-bg { position: fixed; inset: 0; z-index: -2; pointer-events: none; display: none; }
.frost-bg svg { width: 100%; height: 100%; display: block; }
:root:not([data-theme="night"]) .frost-bg { display: block; }
:root:not([data-theme="night"]) {
  --ink: #15181e; --ink-2: #4d5563; --ink-3: #848b98;
  --bg: #e4e7ec;
  --glass: rgba(255, 255, 255, .34);
  --glass-2: rgba(255, 255, 255, .55);
  --glass-edge: rgba(255, 255, 255, .95);
  --hair: rgba(255, 255, 255, .55);
  --hair-2: rgba(20, 26, 38, .10);
  --lift: 0 1px 0 rgba(255,255,255,.85) inset, 0 -1px 0 rgba(255,255,255,.25) inset, 0 24px 50px -24px rgba(40, 50, 70, .35), 0 2px 6px -2px rgba(40, 50, 70, .08);
  --glow-a: transparent; --glow-b: transparent;
  --accent: #3a6ff0; --accent-ink: #ffffff; --accent-soft: rgba(58, 111, 240, .12);
  --cyan: #3a6ff0; --pink: #7c8aa5;
  --up: #12996b; --down: #e0365a; --warn: #c27a0e;
  --panel: rgba(255, 255, 255, .38); --field: rgba(255, 255, 255, .5);

}
:root:not([data-theme="night"]) body { background: var(--bg); }
:root:not([data-theme="night"]) body::before { display: none; }
:root:not([data-theme="night"]) .chart-card, :root:not([data-theme="night"]) .stat, :root:not([data-theme="night"]) .table,
:root:not([data-theme="night"]) .kv .item, :root:not([data-theme="night"]) .trade-box, :root:not([data-theme="night"]) .lock form,
:root:not([data-theme="night"]) .promo, :root:not([data-theme="night"]) .status-card {
  -webkit-backdrop-filter: blur(30px) saturate(140%); backdrop-filter: blur(30px) saturate(140%);
  border: 1px solid rgba(255,255,255,.6);
}
:root:not([data-theme="night"]) .side { background: rgba(255,255,255,.22); border-right: 1px solid rgba(255,255,255,.55); -webkit-backdrop-filter: blur(30px) saturate(140%); backdrop-filter: blur(30px) saturate(140%); }
:root:not([data-theme="night"]) .right { background: rgba(255,255,255,.16); border-left: 1px solid rgba(255,255,255,.55); -webkit-backdrop-filter: blur(30px) saturate(140%); backdrop-filter: blur(30px) saturate(140%); }
:root:not([data-theme="night"]) .head { border-bottom: 1px solid rgba(255,255,255,.5); }
/* selected things lift out as a brighter pane, like the reference's pill */
:root:not([data-theme="night"]) .nav a[aria-current="page"],
:root:not([data-theme="night"]) .tabs button[aria-pressed="true"],
:root:not([data-theme="night"]) .ranges button[aria-pressed="true"] {
  background: rgba(255,255,255,.78); color: var(--ink);
  box-shadow: 0 1px 0 #fff inset, 0 6px 16px -8px rgba(40,50,70,.35), 0 0 0 1px rgba(20,26,38,.06);
}
:root:not([data-theme="night"]) .tabs, :root:not([data-theme="night"]) .search { background: rgba(255,255,255,.4); border: 1px solid rgba(255,255,255,.6); }
:root:not([data-theme="night"]) .tr:not(.h):hover, :root:not([data-theme="night"]) .sig:hover {
  background: rgba(255,255,255,.5); box-shadow: 0 1px 0 #fff inset, 0 8px 20px -14px rgba(40,50,70,.4);
}
:root:not([data-theme="night"]) .tr, :root:not([data-theme="night"]) .sig { border-bottom: 1px solid rgba(255,255,255,.45); }
:root:not([data-theme="night"]) .balance-row .amt { background: none; color: var(--ink); -webkit-text-fill-color: currentColor; }
:root:not([data-theme="night"]) .chip.a { background: rgba(58,111,240,.08); } :root:not([data-theme="night"]) .chip.a i { background: rgba(58,111,240,.14); color: var(--accent); }
:root:not([data-theme="night"]) .chip.b { background: rgba(124,138,165,.1); } :root:not([data-theme="night"]) .chip.b i { background: rgba(124,138,165,.18); color: #5b6782; }
:root:not([data-theme="night"]) .promo { background: radial-gradient(120% 80% at 100% 0%, rgba(58,111,240,.10), transparent 60%), var(--glass); }
:root:not([data-theme="night"]) .promo .meter span { background: linear-gradient(90deg, var(--accent), #8aa6f5); box-shadow: none; }
:root:not([data-theme="night"]) .pill.open, :root:not([data-theme="night"]) .pill.pending { box-shadow: 0 0 0 1px rgba(58,111,240,.25) inset; }
:root:not([data-theme="night"]) .pill.tp, :root:not([data-theme="night"]) .pill.taken { background: rgba(18,153,107,.1); }
:root:not([data-theme="night"]) .pill.sl, :root:not([data-theme="night"]) .pill.failed { background: rgba(224,54,90,.08); }
:root:not([data-theme="night"]) .status-card .badge { box-shadow: 0 0 0 1px rgba(58,111,240,.2) inset; }
:root:not([data-theme="night"]) .icons .dot { box-shadow: none; }
/* the main button: graphite glass, as calm as the rest */
:root:not([data-theme="night"]) .cta {
  color: #fff; background: linear-gradient(180deg, #3b404b, #1d2129);
  box-shadow: 0 1px 0 rgba(255,255,255,.18) inset, 0 14px 30px -14px rgba(20,26,38,.6);
}
:root:not([data-theme="night"]) .cta:hover { box-shadow: 0 1px 0 rgba(255,255,255,.18) inset, 0 18px 36px -14px rgba(20,26,38,.7); }
:root:not([data-theme="night"]) .cta.paused { color: #fff; background: linear-gradient(180deg, #5a7ff2, var(--accent)); box-shadow: 0 1px 0 rgba(255,255,255,.3) inset, 0 14px 30px -14px rgba(58,111,240,.6); }
:root:not([data-theme="night"]) .flat { background: rgba(255,255,255,.35); border-color: rgba(224,54,90,.3); }
:root:not([data-theme="night"]) .flat.armed { background: var(--down); color: #fff; }
:root:not([data-theme="night"]) .acct .l { background: radial-gradient(120% 140% at 0% 0%, rgba(255,255,255,.9), transparent 55%), radial-gradient(120% 140% at 100% 100%, rgba(58,111,240,.22), transparent 60%), rgba(255,255,255,.35); }
:root:not([data-theme="night"]) .acct .r { background: rgba(29,33,41,.86); }
:root:not([data-theme="night"]) .acct-shadow { background: radial-gradient(60% 100% at 50% 0%, rgba(40,50,70,.25), transparent 70%); }
:root:not([data-theme="night"]) .dots i.on { background: var(--ink); }
:root:not([data-theme="night"]) .bellbtn { background: rgba(255,255,255,.4); border-color: rgba(255,255,255,.65); color: var(--ink-2); -webkit-backdrop-filter: blur(20px); backdrop-filter: blur(20px); }
:root:not([data-theme="night"]) .bellbtn[aria-pressed="true"] { color: var(--accent); border-color: rgba(58,111,240,.35); background: rgba(255,255,255,.7); }
:root:not([data-theme="night"]) .notify-toast { background: rgba(255,255,255,.75); color: var(--ink); border: 1px solid rgba(255,255,255,.8); backdrop-filter: blur(24px) saturate(140%); -webkit-backdrop-filter: blur(24px) saturate(140%); }
:root:not([data-theme="night"]) .search:focus-within, :root:not([data-theme="night"]) .lock input:focus { border-color: rgba(58,111,240,.4); }
@media (max-width: 760px) {
  :root:not([data-theme="night"]) .head { background: rgba(236,238,242,.45); }
  :root:not([data-theme="night"]) .bottom-nav { background: rgba(240,242,246,.78); border-top: 1px solid rgba(255,255,255,.8); -webkit-backdrop-filter: blur(30px) saturate(150%); backdrop-filter: blur(30px) saturate(150%); }
  :root:not([data-theme="night"]) .right { background: transparent; }
}
```

## Step 3 — the minimum, if the app is different

If the class names do not match, this is all the look needs:

```css
.frost-bg { position: fixed; inset: 0; z-index: -2; pointer-events: none; }
.frost-bg svg { width: 100%; height: 100%; display: block; }
body { background: #e4e7ec; color: #15181e; }

/* every card / panel */
.glass {
  background: rgba(255,255,255,.34);
  -webkit-backdrop-filter: blur(30px) saturate(140%);
  backdrop-filter: blur(30px) saturate(140%);
  border: 1px solid rgba(255,255,255,.6);
  border-radius: 22px;
  box-shadow:
    0 1px 0 rgba(255,255,255,.85) inset,
    0 -1px 0 rgba(255,255,255,.25) inset,
    0 24px 50px -24px rgba(40,50,70,.35),
    0 2px 6px -2px rgba(40,50,70,.08);
}

/* the selected tab / nav item / row */
.glass-selected {
  background: rgba(255,255,255,.78);
  box-shadow: 0 1px 0 #fff inset, 0 6px 16px -8px rgba(40,50,70,.35), 0 0 0 1px rgba(20,26,38,.06);
}

/* sidebars and headers: lighter glass, never opaque */
.glass-rail {
  background: rgba(255,255,255,.22);
  -webkit-backdrop-filter: blur(30px) saturate(140%);
  backdrop-filter: blur(30px) saturate(140%);
}

/* main button: graphite, not a bright colour */
.btn-primary {
  color: #fff;
  background: linear-gradient(180deg, #3b404b, #1d2129);
  box-shadow: 0 1px 0 rgba(255,255,255,.18) inset, 0 14px 30px -14px rgba(20,26,38,.6);
}
```

Colours: text `#15181e`, secondary text `#4d5563`, muted `#848b98`, accent `#3a6ff0`, profit `#12996b`, loss `#e0365a`. Font: Geist (Google Fonts), numbers in Geist Mono.

## How to check it worked

- Behind the cards you can see soft grey waves, blurred through the glass. If the cards look solid white, either the background is missing or something between them is opaque.
- There are no hard horizontal lines across the background. If there are, the SVG filters are missing `filterUnits="userSpaceOnUse"` and the large region.
- On iPhone Safari the blur works, which needs the `-webkit-` prefix.
