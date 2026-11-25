// Edge Lab · Learn — step-by-step quant lessons in Hebrew, built on the lab's own strategies.
// Each lesson is a sequence of short steps: one idea, one real example, sometimes a question or a calculator.
// Self-contained (no imports): used by the local app (views/learn.js) and by the published page (served as learn.js).
// mountLearn(root, strategies) — strategies come from normalise(): win (%), avg (R), avgWin, avgLoss, sd, n, t, worstStreak, mc…
// RULE: when research changes a strategy, a gate or a method, update the lesson that explains it (see CLAUDE.md).

const CSS = `
.lx{--lx-fg:var(--fg,#f5f5f5);--lx-mut:var(--fg-2,var(--muted,#888));--lx-dim:var(--muted,#555);--lx-line:var(--border-soft,var(--line,#222));--lx-card:var(--card,var(--panel,#101010));--lx-acc:var(--accent,#e74747);
  direction:rtl;text-align:right;color:var(--lx-fg);display:grid;grid-template-columns:240px minmax(0,1fr);gap:32px;align-items:start;font-size:15px;line-height:1.75}
.lx *{box-sizing:border-box}
.lx-nav{position:sticky;top:var(--lx-top,16px);display:flex;flex-direction:column;gap:2px}
.lx-nav button{all:unset;cursor:pointer;display:grid;grid-template-columns:22px 1fr;gap:8px;align-items:center;padding:8px 10px;border-radius:8px;color:var(--lx-mut);font-size:13.5px;line-height:1.4}
.lx-nav button:hover{color:var(--lx-fg);background:rgba(127,127,127,.08)}
.lx-nav button[aria-current="true"]{color:var(--lx-fg);background:rgba(127,127,127,.13)}
.lx-nav button:focus-visible,.lx button:focus-visible{outline:1.5px solid var(--lx-acc);outline-offset:2px}
.lx-nav i{font-style:normal;font-size:11px;color:var(--lx-dim);text-align:center;font-family:var(--mono,ui-monospace,monospace)}
.lx-nav i.done{color:var(--lx-fg)}
.lx-nav .lx-lvl{font-size:11px;color:var(--lx-dim);padding:12px 10px 4px}
.lx-body{min-width:0;max-width:680px}
.lx-top{display:flex;align-items:center;gap:12px;margin-bottom:6px}
.lx-eyebrow{font-size:12px;color:var(--lx-dim)}
.lx-bar{flex:1;height:3px;background:var(--lx-line);border-radius:2px;overflow:hidden}
.lx-bar b{display:block;height:100%;background:var(--lx-acc);border-radius:2px;transition:width .4s cubic-bezier(.2,.7,.2,1)}
.lx-cnt{font-size:12px;color:var(--lx-dim);font-family:var(--mono,ui-monospace,monospace);direction:ltr}
.lx h2{font-size:23px;font-weight:500;letter-spacing:-.02em;margin:6px 0 18px;line-height:1.35}
.lx-steps{display:flex;flex-direction:column;gap:14px}
.lx-step{padding:18px 20px;border:1px solid var(--lx-line);border-radius:14px;background:var(--lx-card);animation:lx-in .45s cubic-bezier(.2,.7,.2,1) both}
.lx-step.past{opacity:.55;transition:opacity .3s}
.lx-step.past:hover{opacity:1}
@keyframes lx-in{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.lx-step p{margin:0 0 10px}.lx-step p:last-child{margin-bottom:0}
.lx-step .lx-h{font-size:12px;color:var(--lx-dim);margin-bottom:6px}
.lx b{font-weight:600}
.lx-f{direction:ltr;text-align:center;font-family:var(--mono,ui-monospace,monospace);font-size:17px;padding:16px 14px;margin:12px 0;border:1px solid var(--lx-line);border-radius:10px;background:rgba(127,127,127,.04);overflow-x:auto;white-space:nowrap}
.lx-f small{display:block;font-size:11.5px;color:var(--lx-dim);margin-top:8px;font-family:var(--sans,system-ui,sans-serif);white-space:normal;direction:rtl}
.lx-frac{display:inline-flex;flex-direction:column;vertical-align:middle;text-align:center;margin:0 4px}
.lx-frac>span:first-child{border-bottom:1px solid currentColor;padding:0 4px 2px}.lx-frac>span:last-child{padding:2px 4px 0}
.lx-n{font-family:var(--mono,ui-monospace,monospace);direction:ltr;unicode-bidi:isolate;white-space:nowrap}
.lx-ex{border-right:2px solid var(--lx-acc);padding:10px 14px;margin:10px 0 0;background:rgba(231,71,71,.05);border-radius:8px 0 0 8px;font-size:14.5px}
.lx-ex .lx-exh{font-size:11.5px;color:var(--lx-dim);margin-bottom:4px}
.lx-calc{display:grid;grid-template-columns:auto 1fr auto;gap:6px 14px;align-items:center;direction:rtl;font-family:var(--mono,ui-monospace,monospace);font-size:14px;margin:10px 0 0}
.lx-calc .lbl{direction:rtl;font-family:var(--sans,system-ui,sans-serif);color:var(--lx-mut);font-size:13px;text-align:right}
.lx-calc span:not(.lbl){direction:ltr;unicode-bidi:isolate}.lx-calc span:nth-child(3n+2){text-align:center;color:var(--lx-mut)}.lx-calc .res{text-align:left}
.lx-calc .sum{border-top:1px solid var(--lx-line);padding-top:6px;font-weight:600}
.lx-q{margin-top:6px}.lx-q .lx-qa{display:flex;flex-direction:column;gap:8px;margin-top:10px}
.lx-q button{all:unset;cursor:pointer;padding:10px 14px;border:1px solid var(--lx-line);border-radius:10px;font-size:14px;transition:border-color .15s,background .15s}
.lx-q button:hover:not([disabled]){border-color:var(--lx-mut)}
.lx-q button[disabled]{cursor:default}
.lx-q button.right{border-color:var(--pos,#d9d9d9);background:rgba(217,217,217,.08)}
.lx-q button.wrong{border-color:var(--lx-acc);background:rgba(231,71,71,.07)}
.lx-fb{margin-top:10px;font-size:14px;animation:lx-in .35s both}
.lx-play{border:1px dashed var(--lx-line);border-radius:12px;padding:12px 14px;margin-top:10px}
.lx-row{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end}
.lx-in{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--lx-mut);min-width:100px;flex:1}
.lx-in input{direction:ltr;font:inherit;font-family:var(--mono,ui-monospace,monospace);font-size:14px;color:var(--lx-fg);background:transparent;border:1px solid var(--lx-line);border-radius:8px;height:34px;padding:0 10px;width:100%}
.lx-in input:focus{outline:none;border-color:var(--lx-acc)}
.lx-out{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:1px;margin-top:12px;border:1px solid var(--lx-line);border-radius:10px;overflow:hidden;background:var(--lx-line)}
.lx-out div{background:var(--lx-card);padding:9px 12px}.lx-out span{display:block;font-size:11.5px;color:var(--lx-dim)}
.lx-out b{font-family:var(--mono,ui-monospace,monospace);font-weight:500;font-size:16px;direction:ltr;display:block;text-align:right}
.lx-pos{color:var(--pos,var(--lx-fg))}.lx-neg{color:var(--lx-acc)}
.lx table.lx-tbl{width:100%;min-width:0;border-collapse:collapse;margin:8px 0 0;font-size:13px}
.lx table.lx-tbl th{font-family:inherit;text-transform:none;letter-spacing:0;background:none;font-size:12px;font-weight:400;color:var(--lx-dim);text-align:right;padding:6px 8px;border-bottom:1px solid var(--lx-line)}
.lx table.lx-tbl td{padding:7px 8px;border-bottom:1px solid var(--lx-line);font-family:var(--mono,ui-monospace,monospace);direction:ltr;text-align:right}
.lx table.lx-tbl td:first-child{font-family:inherit;direction:rtl}
.lx-key{border-color:var(--lx-acc);background:rgba(231,71,71,.04)}
.lx-actions{display:flex;gap:10px;align-items:center;margin-top:18px;flex-wrap:wrap;scroll-margin-bottom:150px}
.lx-step{scroll-margin-bottom:150px}
.lx-go{all:unset;cursor:pointer;padding:10px 22px;border-radius:10px;background:var(--lx-fg);color:var(--bg,#0a0a0a);font-weight:500;font-size:14px;transition:opacity .15s,transform .1s}
.lx-go:hover{opacity:.9}.lx-go:active{transform:translateY(1px)}
.lx-go[disabled]{opacity:.3;cursor:default}
.lx-ghost{all:unset;cursor:pointer;padding:10px 14px;border-radius:10px;color:var(--lx-mut);font-size:13.5px}
.lx-ghost:hover{color:var(--lx-fg)}
.lx-hint{font-size:12px;color:var(--lx-dim)}
@media (max-width:820px){.lx{grid-template-columns:1fr}.lx-nav{position:static;flex-direction:row;overflow-x:auto;gap:4px;padding-bottom:6px}.lx-nav button{grid-template-columns:auto auto;white-space:nowrap}.lx-nav .lx-lvl{display:none}}
@media (prefers-reduced-motion:reduce){.lx-step,.lx-fb{animation:none}}
`;

const n = (x, d = 2) => (x == null || !Number.isFinite(+x) ? "—" : (+x).toFixed(d));
const sg = (x, d = 3) => (x == null || !Number.isFinite(+x) ? "—" : `${x > 0 ? "+" : x < 0 ? "−" : ""}${Math.abs(x).toFixed(d)}`);
const N = (s) => `<span class="lx-n">${s}</span>`;
const frac = (a, b) => `<span class="lx-frac"><span>${a}</span><span>${b}</span></span>`;
const cls = (x) => (x > 0 ? "lx-pos" : x < 0 ? "lx-neg" : "");
const ex = (h, body) => `<div class="lx-ex"><div class="lx-exh">${h}</div>${body}</div>`;
const num = (s) => parseFloat(String(s).replace("−", "-").replace(/[^0-9.\-]/g, ""));
const calcRows = (rows) => `<div class="lx-calc">${rows.map(([l, f, r, sum]) => `<span class="lbl ${sum ? "sum" : ""}">${l}</span><span class="${sum ? "sum" : ""}">${f}</span><span class="res ${sum ? "sum" : ""} ${cls(num(r))}">${r}</span>`).join("")}</div>`;
const tbl = (head, rows) => `<table class="lx-tbl"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c ?? "—"}</td>`).join("")}</tr>`).join("")}</tbody></table>`;

/**
 * Lessons: { id, level, title, steps: [step] }.
 * step: { h?: small heading, html, q?: { ask, options, answer, explain }, play?: { inputs, update }, key?: true }
 */
function lessons(S) {
  const by = (id) => S.find((s) => s.id === id) || {};
  const r10 = by("rdm10"), rdm = by("rdm"), gt = by("gotobi"), sp = by("sp"), avp = by("avp");
  const p10 = (r10.win ?? 0) / 100, pR = (rdm.win ?? 0) / 100, pG = (gt.win ?? 0) / 100;
  const L10 = -(r10.avgLoss ?? -1), LR = -(rdm.avgLoss ?? -1), LG = -(gt.avgLoss ?? -1);
  const bR = (rdm.avgWin ?? 1) / LR, kellyR = pR - (1 - pR) / bR;
  const streak10 = r10.n ? Math.log(r10.n) / Math.log(1 / (1 - p10)) : null;
  const need = (s) => (s.avg > 0 && s.sd ? Math.ceil(((2 * s.sd) / s.avg) ** 2) : null);
  const tMonth = r10.sd ? r10.avg / (r10.sd / Math.sqrt(20)) : null;
  const ws = r10.worstStreak || 0;

  return [
    { id: "expectancy", level: "יסודות", title: "תוחלת: כמה עסקה ממוצעת שווה", steps: [
      { h: "נתחיל משאלה", html: `<p>שתי אסטרטגיות אמיתיות מהמעבדה שלנו:</p><p><b>A</b> מנצחת ב־${N(n(rdm.win, 1) + "%")} מהעסקאות.<br><b>B</b> מנצחת רק ב־${N(n(r10.win, 1) + "%")} מהעסקאות.</p>`,
        q: { ask: "איזו מהן מרוויחה יותר על כל עסקה?", options: ["A, כי היא מנצחת יותר", "B", "אי אפשר לדעת רק מאחוז ההצלחה"], answer: 2,
          explain: `אחוז הצלחה לבד לא אומר כלום. בפועל B (זו RDM 1:10) מרוויחה ${N(sg(r10.avg, 3) + "R")} לעסקה, ו־A (‏RDM הרגיל) ${N(sg(rdm.avg, 3) + "R")}. כדי להבין למה, צריך שני מושגים.` } },
      { h: "מושג 1: R", html: `<p><b>R</b> הוא כמה אתה מסכן בעסקה, כלומר המרחק לסטופ.</p>
        ${ex("דוגמה ב־NQ", `סטופ במרחק ${N("20")} נקודות = ${N("1R")}.<br>היעד נפגע אחרי ${N("60")} נקודות → ${N("+3R")}.<br>הסטופ נפגע → ${N("−1R")}.`)}
        <p style="margin-top:10px">למה ב־R ולא בדולרים? כי ככה אפשר להשוות אסטרטגיות עם סטופים וגדלים שונים.</p>` },
      { h: "מושג 2: שני מספרים, לא אחד", html: `<p>כדי לדעת אם אסטרטגיה טובה, צריך:</p><p>1. <b>p</b>: כמה פעמים היא מנצחת.<br>2. <b>W ו־L</b>: כמה R היא מרוויחה בממוצע כשהיא מנצחת, וכמה היא מפסידה כשהיא מפסידה.</p>
        ${ex("RDM 1:10", N(`p = ${n(p10, 3)} · W = ${sg(r10.avgWin, 2)}R · L = ${n(L10, 2)}R`))}` },
      { h: "הנוסחה, חלק אחרי חלק", html: `<div class="lx-f">E[R] = p · W − (1 − p) · L<small>מה מכניסים הניצחונות, פחות מה עולים ההפסדים</small></div>
        ${calcRows([["מהניצחונות", `${n(p10, 3)} × ${n(r10.avgWin, 2)}`, sg(p10 * r10.avgWin, 3)], ["מההפסדים", `${n(1 - p10, 3)} × ${n(L10, 2)}`, sg(-(1 - p10) * L10, 3)], ["תוחלת לעסקה", "", sg(r10.avg, 3) + "R", true]])}
        <p style="margin-top:12px">ההפסדים רבים אבל קטנים. הניצחונות מעטים אבל ענקיים. ביחד: חיובי.</p>` },
      { h: "מה זה אומר בכסף", html: `<p>אם כל ${N("1R")} שווה ${N("$500")}:</p>
        ${calcRows([["על 100 עסקאות", `100 × ${sg(r10.avg, 3)}R`, sg(100 * r10.avg, 1) + "R"], ["בדולרים", "× $500", "+$" + n(100 * r10.avg * 500, 0), true]])}
        <p style="margin-top:12px">וזה כשבכל אחת מ־100 העסקאות הסיכוי להפסיד הוא כמעט 80%.</p>` },
      { h: "תורך", html: ex("Gotobi", N(`p = ${n(pG, 3)} · W = ${sg(gt.avgWin, 2)}R · L = ${n(LG, 2)}R`)),
        q: { ask: "התוחלת של Gotobi חיובית?", options: ["כן", "לא"], answer: 0,
          explain: `${N(`${n(pG, 3)} × ${n(gt.avgWin, 2)} − ${n(1 - pG, 3)} × ${n(LG, 2)} = ${sg(gt.avg, 3)}R`)}. חיובית, ובדרך הפוכה מ־1:10: הרבה ניצחונות בינוניים.` } },
      { h: "שחק עם זה", html: "<p>שנה את המספרים וראה מתי התוחלת עוברת את האפס.</p>",
        play: { inputs: [["p", "אחוז הצלחה (%)", 48, 0.5], ["w", "רווח ממוצע (R)", 2, 0.1], ["l", "הפסד ממוצע (R)", 1, 0.1]],
          update(v) { const p = v.p / 100, e = p * v.w - (1 - p) * v.l; return [["תוחלת לעסקה", `${sg(e, 3)}R`, cls(e)], ["הצלחה מינימלית", `${n((100 * v.l) / (v.w + v.l), 1)}%`], ["על 100 עסקאות", `${sg(e * 100, 1)}R`, cls(e)]]; } } },
      { key: true, html: `<p><b>השורה התחתונה:</b> אל תשאל "מה אחוז ההצלחה". שאל "מה התוחלת ב־R".</p>` },
    ] },

    { id: "winrate", level: "יסודות", title: "למה 98% הצלחה יכול להיות מלכודת", steps: [
      { h: "תרחיש", html: `<p>מוכרים לך בוט: "98% הצלחה!"</p>`,
        q: { ask: "מה השאלה הראשונה שאתה שואל?", options: ["כמה הוא עולה", "מה הרווח הממוצע מול ההפסד הממוצע", "כמה עסקאות הוא עושה ביום"], answer: 1,
          explain: "בדיוק. מהשיעור הקודם: אחוז הצלחה בלי W ו־L לא אומר כלום. עכשיו נראה איך מייצרים 98% מכלום." } },
      { h: "איך מייצרים 98%", html: `<p>שמים יעד קרוב מאוד וסטופ רחוק מאוד.</p>${ex("ב־NQ", `יעד: ${N("2")} נקודות · סטופ: ${N("100")} נקודות.<br>היעד נפגע כמעט תמיד. הסטופ כמעט אף פעם, עד שהוא כן.`)}` },
      { h: "החשבון", html: `<p>סטופ של 100 נקודות = ${N("1R")}, אז יעד של 2 נקודות = ${N("0.02R")}.</p>
        ${calcRows([["98 ניצחונות", "98 × 0.02", "+1.96R"], ["2 הפסדים", "2 × 1", "−2.00R"], ["על 100 עסקאות", "", "−0.04R", true]])}
        <p style="margin-top:12px">98% הצלחה, ומפסיד. ועוד לא שילמת עמלות.</p>` },
      { h: "כמה הצלחה צריך באמת", html: `<div class="lx-f">p* = ${frac("1", "1 + RR")}<small>אחוז ההצלחה המינימלי כדי לא להפסיד, כש־RR הוא היחס בין היעד לסטופ</small></div>
        ${tbl(["יחס רווח־סיכון", "הצלחה מינימלית"], [0.02, 0.5, 1, 2, 3, 10].map((rr) => [`1:${rr}`, `${n(100 / (1 + rr), 1)}%`]))}` },
      { h: "ראינו את זה אצלנו", html: ex("AVP Zones", `על הגרף ב־TradingView הסימנים נראו כמו 100% הצלחה, כי בדיעבד רואים רק את האזורים שעבדו.<br>בבדיקה על 14 שנה, עם עלויות: ${N(sg(avp.avg, 3) + "R")} לעסקה.`) },
      { h: "שלוש שאלות לכל מוכר", html: "<p>1. מה הרווח הממוצע מול ההפסד הממוצע?<br>2. יש הכפלת פוזיציה אחרי הפסד (מרטינגייל)?<br>3. מה רצף ההפסדים הארוך ביותר, ומה הירידה הגדולה ביותר?</p><p>מי שעונה \"אין הפסדים\" לא אומר את האמת, או שלא בדק.</p>" },
      { key: true, html: `<p><b>השורה התחתונה:</b> אחוז הצלחה גבוה הוא מספר שיווקי, לא מדד ביצוע.</p>` },
    ] },

    { id: "sizing", level: "יסודות", title: "גודל פוזיציה ו־Kelly", steps: [
      { h: "שני סוחרים, אותה אסטרטגיה", html: `<p>שניהם סוחרים RDM 1:10. הראשון מסכן ${N("1%")} מהחשבון בעסקה, השני ${N("10%")}.</p><p>שניהם יפגשו את רצף ההפסדים הארוך של האסטרטגיה: ${N(ws)} הפסדים ברצף.</p>`,
        q: { ask: "כמה נשאר לסוחר של 10% אחרי הרצף?", options: ["בערך 70% מהחשבון", "בערך 30% מהחשבון", "פחות מ־5% מהחשבון"], answer: 2,
          explain: `${N(`0.90^${ws} = ${n(100 * 0.9 ** ws, 1)}%`)} מהחשבון נשאר. לסוחר של 1%: ${N(`0.99^${ws} = ${n(100 * 0.99 ** ws, 1)}%`)}. אותה אסטרטגיה, אחד שורד ואחד לא.` } },
      { h: "אחוז קבוע מהחשבון", html: `<p>השיטה הנפוצה: מסכנים אחוז קבוע מהחשבון. אם ${N("1R = 1%")}, עסקה של ${N("+3R")} היא ${N("+3%")}.</p><p>השאלה היא איזה אחוז. לזה יש נוסחה.</p>` },
      { h: "נוסחת Kelly", html: `<div class="lx-f">f* = p − ${frac("1 − p", "b")}<small>f* = החלק מההון לסכן בעסקה · p = אחוז הצלחה · b = רווח ממוצע חלקי הפסד ממוצע</small></div><p>זה הגודל שמביא לצמיחה הכי מהירה של החשבון לאורך זמן, בתנאי שהמספרים מדויקים.</p>` },
      { h: "על RDM", html: calcRows([["p", "", n(pR, 3)], ["b", `${n(rdm.avgWin, 2)} / ${n(LR, 2)}`, n(bR, 2)], ["Kelly מלא", `${n(pR, 3)} − ${n(1 - pR, 3)} / ${n(bR, 2)}`, `${n(100 * kellyR, 1)}%`, true]]) + `<p style="margin-top:12px">${N(n(100 * kellyR, 0) + "%")} מהחשבון בעסקה אחת. נשמע הרבה? כי זה הרבה.</p>` },
      { h: "למה אף אחד לא משתמש ב־Kelly מלא", html: "<p>Kelly מלא גורם לתנודות של עשרות אחוזים. ואם הערכת את p קצת גבוה מדי, אתה כבר מעבר לגודל הנכון ומפסיד.</p><p>מקצוענים משתמשים ב<b>חצי Kelly</b> או ב<b>רבע Kelly</b>. מקבלים בערך 75% מהצמיחה עם הרבה פחות כאב.</p>" },
      { h: "שאלה", html: "", q: { ask: "Kelly יצא שלילי. מה זה אומר?", options: ["צריך לסכן פחות", "אין יתרון, הגודל הנכון הוא אפס", "צריך לעבור לשורט"], answer: 1, explain: "Kelly שלילי אומר שהתוחלת שלילית. אין גודל פוזיציה שהופך אסטרטגיה מפסידה לרווחית." } },
      { h: "שחק עם זה", html: "", play: { inputs: [["p", "אחוז הצלחה (%)", 52, 0.5], ["b", "רווח / הפסד", 1.3, 0.05]],
          update(v) { const p = v.p / 100, f = p - (1 - p) / v.b; return [["Kelly מלא", `${n(f * 100, 1)}%`, cls(f)], ["חצי", `${n(f * 50, 1)}%`, cls(f)], ["רבע", `${n(f * 25, 1)}%`, cls(f)]]; } } },
      { key: true, html: `<p><b>השורה התחתונה:</b> גודל פוזיציה לא יוצר יתרון, אבל גודל שגוי הורס יתרון קיים.</p>` },
    ] },

    { id: "tstat", level: "סטטיסטיקה", title: "מובהקות: יתרון או מזל", steps: [
      { h: "מטבע", html: "<p>הטלת מטבע 10 פעמים, ויצא עץ 7 פעמים.</p>", q: { ask: "המטבע מזויף?", options: ["כן, 70% זה הרבה", "לא, הוא הוגן", "אי אפשר לדעת מ־10 הטלות"], answer: 2,
          explain: "מטבע הוגן נותן 7 מתוך 10 או יותר בערך פעם ב־6 ניסיונות. 10 הטלות זה פשוט מעט מדי. אותו דבר עם עסקאות." } },
      { h: "הרעש של הממוצע", html: `<p>כל ממוצע שמדדת "רועד": אם תריץ את אותה אסטרטגיה בתקופה אחרת, תקבל ממוצע קצת אחר. כמה הוא רועד?</p><div class="lx-f">רעש = ${frac("s", "√n")}<small>s = כמה העסקאות מתפזרות (סטיית תקן) · n = מספר העסקאות</small></div><p>יותר עסקאות → פחות רעש.</p>` },
      { h: "t-stat: יחס אות לרעש", html: `<div class="lx-f">t = ${frac("ממוצע", "רעש")} = ${frac("R̄", "s / √n")}</div>
        ${ex("Gotobi", calcRows([["רעש", `${n(gt.sd, 2)} / √${gt.n}`, n(gt.sd / Math.sqrt(gt.n || 1), 3)], ["ממוצע", "", sg(gt.avg, 3)], ["t", "", n(gt.t, 2), true]]))}
        <p style="margin-top:10px">הממוצע גדול פי ${N(n(gt.t, 1))} מהרעש. זה לא מזל.</p>` },
      { h: "כמה זה מספיק", html: "<p><b>t ≈ 2</b>: בערך 5% סיכוי שזה מזל, אם זה המבחן היחיד שהרצת.<br><b>t ≥ 3</b>: הרף שלנו, כי אנחנו מריצים הרבה מבחנים (שיעור הבא).</p>" },
      { h: "חודש אחד", html: `<p>נגיד שסחרת RDM 1:10 חודש אחד, בערך 20 עסקאות, וקיבלת בדיוק את הממוצע שלה.</p>${calcRows([["רעש", `${n(r10.sd, 2)} / √20`, n((r10.sd || 0) / Math.sqrt(20), 3)], ["t", `${sg(r10.avg, 3)} / רעש`, n(tMonth, 2), true]])}
        <p style="margin-top:12px">t של ${N(n(tMonth, 2))}. מחודש אחד אי אפשר לדעת כלום, גם כשהאסטרטגיה טובה. וזה נכון גם לחודש של 400 אלף שקל.</p>` },
      { h: "כמה עסקאות צריך", html: `<div class="lx-f">n ≈ (${frac("2 · s", "R̄")})²<small>כמה עסקאות כדי להגיע ל־t = 2</small></div>${tbl(["אסטרטגיה", "צריך", "יש"], [[gt.name || "Gotobi", need(gt), gt.n], [rdm.name || "RDM", need(rdm), rdm.n], [r10.name || "RDM 1:10", need(r10), r10.n]])}<p style="margin-top:10px">ל־1:10 צריך הרבה יותר הוכחה, כי העסקאות שלה מתפזרות בפראות.</p>` },
      { h: "שחק עם זה", html: "", play: { inputs: [["m", "ממוצע R̄", 0.15, 0.01], ["s", "סטיית תקן s", 1.5, 0.1], ["n", "עסקאות", 200, 10]],
          update(v) { const t = v.m / (v.s / Math.sqrt(v.n)); return [["t עכשיו", n(t, 2), t >= 2 ? "lx-pos" : "lx-neg"], ["ל־t=2", n(((2 * v.s) / v.m) ** 2, 0)], ["ל־t=3", n(((3 * v.s) / v.m) ** 2, 0)]]; } } },
      { key: true, html: `<p><b>השורה התחתונה:</b> יתרון אמיתי מוכיחים במאות ואלפי עסקאות, לא בחודש טוב.</p>` },
    ] },

    { id: "multiple", level: "סטטיסטיקה", title: "בדיקות מרובות ו־Overfitting", steps: [
      { h: "ניסוי מחשבה", html: "<p>בודקים 1,000 אסטרטגיות אקראיות לגמרי, בלי שום יתרון. כל אחת \"עוברת\" אם יש לה רק 5% סיכוי להיות מזל.</p>",
        q: { ask: "בערך כמה יעברו?", options: ["אף אחת", "בערך 50", "בערך 500"], answer: 1, explain: "1,000 × 5% = 50. חמישים אסטרטגיות חסרות ערך שנראות מוכחות. ואם בוחרים את הטובה מביניהן, בוחרים את בעלת המזל הגדול ביותר." } },
      { h: "הנוסחה", html: `<div class="lx-f">E[מזל] = N · α<small>N = מספר המבחנים · α = הסיכוי למזל בכל מבחן</small></div><p>ככל שבודקים יותר רעיונות, יותר רעיונות גרועים נראים טוב.</p>` },
      { h: "המפעל הגדול שלנו", html: ex("Layers · גאפים רב־שכבתיים", `בדקנו ${N("13,271,040")} אסטרטגיות.<br>עברו את הרף: ${N("17")}.<br>אבל בגרסה האקראית של אותו מפעל עברו ${N("22")}.<br>ורק אחת מה־17 הרוויחה בשנים 2022–26.`) + "<p style=\"margin-top:10px\">כל ה\"מנצחות\" היו מזל.</p>" },
      { h: "ומפעל שכן מצא", html: ex("מפעל התיאוריות הראשון", `יצאו ${N("142")} אסטרטגיות מול ${N("2")} בפלסבו: פי 70 יותר מהאקראי.<br>מתוכו נולד RDM.`) },
      { h: "שלוש הגנות", html: "<p>1. <b>רף גבוה</b>: t ≥ 3 ולא 2.<br>2. <b>שלבים</b>: לעבור ב־2012–17, אחר כך ב־2018–21, ורק אז מבט אחד על 2022–26.<br>3. <b>מפעל פלסבו</b>: אותו חיפוש על נתונים מעורבבים. מה שחשוב זה כמה <b>יותר</b> מהאקראי יצא.</p>" },
      { key: true, html: `<p><b>השורה התחתונה:</b> השאלה היא לא "כמה עברו", אלא "כמה עברו יותר מהאקראי".</p>` },
    ] },

    { id: "placebo", level: "סטטיסטיקה", title: "המבחן מול אקראי", steps: [
      { h: "הרעיון", html: "<p>רוצים לדעת אם הכלל שלך עושה משהו? בונים \"תאום\" שזהה לו בכל דבר, <b>חוץ מהחלק שאמור להיות הסוד</b>, ומשווים.</p>" },
      { h: "איך שוברים את הסוד", html: "<p>אם הסוד הוא שעה, <b>מזיזים את השעון</b>.<br>אם הסוד הוא תאריך, <b>מגרילים ימים</b>.<br>אם הסוד הוא הכיוון, <b>מגרילים לונג או שורט</b>.<br>אם הסוד הוא רמת מחיר, <b>מזיזים את הרמות</b>.</p>" },
      { h: "המספר", html: `<div class="lx-f">p = ${frac("ריצות אקראיות שהצליחו לפחות כמוך", "כל הריצות האקראיות")}</div>
        ${ex("AVP Zones", `הזזנו את האזורים למקומות אקראיים. ${N("42%")} מהריצות האקראיות הרוויחו לפחות כמו האזורים "האמיתיים".<br>כלומר האזורים עצמם לא עושים כלום.`)}` },
      { h: "שאלה", html: "", q: { ask: "הרצת 1,000 תאומים אקראיים, ו־3 מהם הצליחו כמו האסטרטגיה שלך. מה ה־p?", options: ["0.3", "0.03", "0.003"], answer: 2, explain: `3 / 1,000 = 0.003. כמעט אף תאום אקראי לא מגיע אליך, אז כנראה יש פה משהו אמיתי. ל־RDM יצא p ${N(rdm.p ?? "—")}, ול־Gotobi ‏${N(gt.p ?? "—")}.` } },
      { h: "נקודה עדינה", html: `<p>באסטרטגיה עם יעד גדול, כמו 1:10, גם <b>כיוון אקראי</b> מרוויח בממוצע: ההפסדים קטנים והרווחים ענקיים.</p>${ex("RDM 1:10", `החציון של הפלסבו: ${N("+0.16R")}. האמיתית: ${N(sg(r10.avg, 2) + "R")}, ובשנים 2020–26 ${N(sg(r10.oosAvg, 2) + "R")}.`)}<p style="margin-top:10px">לכן משווים לפלסבו ולא לאפס.</p>` },
      { key: true, html: `<p><b>השורה התחתונה:</b> אם גרסה אקראית של הרעיון עושה אותו דבר, אין לך רעיון.</p>` },
    ] },

    { id: "oos", level: "סטטיסטיקה", title: "In-sample ו־Out-of-sample", steps: [
      { h: "מבחן עם התשובות", html: "<p>אם ראית את התשובות לפני המבחן, ציון 100 לא אומר שאתה יודע את החומר.</p><p>אסטרטגיה שכיילו על נתונים מסוימים \"ראתה את התשובות\" של הנתונים האלה.</p>" },
      { h: "החלוקה שלנו", html: "<p><b>In-sample (2012–19)</b>: כאן מותר לחפש, לכייל ולבחור.<br><b>Out-of-sample (2020–26)</b>: כאן מסתכלים <b>פעם אחת</b>.</p><p>אם חזרת לכייל אחרי שהסתכלת, השנים האלה כבר \"נשרפו\".</p>" },
      { h: "התוצאות האמיתיות", html: tbl(["אסטרטגיה", "2012–19", "2020–26"], [gt, rdm, r10, sp].filter((s) => s.name).map((s) => [s.name, `<span class="${cls(s.isAvg)}">${sg(s.isAvg, 3)}</span>`, `<span class="${cls(s.oosAvg)}">${sg(s.oosAvg, 3)}</span>`])) },
      { h: "שאלה", html: "", q: { ask: "RDM 1:10 הייתה שלילית ב־2012–19 וחיובית חזק ב־2020–26. מה הכי נכון להסיק?", options: ["מעולה, היא רק משתפרת", "צריך להיזהר: חלק מהכוח שלה תלוי בתנודתיות של השנים האחרונות", "היא מזל וצריך לזרוק אותה"], answer: 1,
          explain: "המבחן מול אקראי עבר, אז היא לא מזל. אבל ההבדל בין התקופות אומר שהיא תלויה במצב השוק, ולכן גודל הפוזיציה צריך להיות זהיר." } },
      { key: true, html: `<p><b>השורה התחתונה:</b> תוצאה מושלמת על כל הנתונים, בלי חלוקה, היא כמעט תמיד overfitting.</p>` },
    ] },

    { id: "montecarlo", level: "סיכון", title: "Monte Carlo: אלפי עתידים", steps: [
      { h: "הבעיה", html: "<p>ההיסטוריה שקרתה היא רק סדר אחד של העסקאות. אם אותן עסקאות היו מגיעות בסדר אחר, אולי הרצף הגרוע היה בא בהתחלה ומחסל את החשבון.</p>" },
      { h: "הרעיון", html: "<p>לוקחים את העסקאות האמיתיות, ושולפים מהן באקראי (עם החזרה) \"שנה\" חדשה.</p><p>חוזרים על זה 5,000 פעמים ומקבלים 5,000 שנים אפשריות.</p>" },
      { h: "מה מודדים", html: `<p><b>חציון</b>: השנה ה"רגילה".<br><b>אחוזון 5</b>: שנה רעה, בערך פעם ב־20 שנה.<br><b>ירידה באחוזון 95</b>: הירידה שצריך להיערך אליה.</p>
        ${tbl(["", "Gotobi", "RDM 1:10"], [["שנים חיוביות", `${n(gt.mc?.p_year_pos, 1)}%`, `${n(r10.mc?.p_year_pos, 1)}%`], ["שנה חציונית", `${sg(gt.mc?.median_year, 1)}R`, `${sg(r10.mc?.median_year, 1)}R`], ["שנה רעה (5%)", `${sg(gt.mc?.p5_year, 1)}R`, `${sg(r10.mc?.p5_year, 1)}R`], ["ירידה (95%)", `${n(gt.mc?.p95_dd, 1)}R`, `${n(r10.mc?.p95_dd, 1)}R`]])}` },
      { h: "שאלה", html: "", q: { ask: "לפי הטבלה, באיזו אסטרטגיה קל יותר להחזיק מעמד?", options: ["Gotobi", "RDM 1:10"], answer: 0, explain: `ב־Gotobi כ־${N(n(gt.mc?.p_year_pos, 0) + "%")} מהשנים חיוביות והירידה קטנה. ב־RDM 1:10 רק כ־${N(n(r10.mc?.p_year_pos, 0) + "%")}, עם ירידה של ${N(n(r10.mc?.p95_dd, 0) + "R")}. התוחלת של 1:10 גבוהה יותר, אבל הדרך הרבה יותר קשה.` } },
      { h: "המגבלה", html: "<p>השליפה בלתי תלויה, אז רצפים ושינויים במצב השוק לא נשמרים. גרסה זהירה יותר שולפת <b>רצפים</b> של עסקאות (block bootstrap).</p>" },
      { key: true, html: `<p><b>השורה התחתונה:</b> אל תשאל רק "כמה ארוויח". שאל "איזו ירידה אצטרך לשרוד בדרך".</p>` },
    ] },

    { id: "streaks", level: "סיכון", title: "רצפי הפסדים", steps: [
      { h: "נחש", html: `<p>RDM 1:10 מנצחת ב־${N(n(r10.win, 0) + "%")} מהעסקאות, ובבדיקה היו ${N(r10.n ?? "—")} עסקאות.</p>`,
        q: { ask: "מה רצף ההפסדים הארוך ביותר שצריך לצפות לו?", options: ["בערך 8", "בערך 15", "בערך 30"], answer: 2, explain: `הנוסחה צופה כ־${N(n(streak10, 0))}. בפועל היו ${N(ws)} הפסדים ברצף.` } },
      { h: "הנוסחה", html: `<div class="lx-f">L<sub>max</sub> ≈ ${frac("ln(n)", "ln(1 / (1 − p))")}<small>n = מספר העסקאות · p = אחוז ההצלחה</small></div>${calcRows([["ln(n)", `ln(${r10.n})`, n(Math.log(r10.n || 1), 2)], ["ln(1/(1−p))", `ln(1/${n(1 - p10, 3)})`, n(Math.log(1 / (1 - p10)), 3)], ["רצף צפוי", "", n(streak10, 0), true]])}` },
      { h: "למה זה חשוב", html: "<p>רוב הסוחרים זונחים אסטרטגיה טובה באמצע רצף <b>רגיל לגמרי</b>. מי שלא ידע שצפוי רצף של 30 היה עוצר אחרי 15 ומפספס את הרווח.</p>" },
      { h: "טבלה", html: tbl(["אחוז הצלחה", "ב־100 עסקאות", "ב־1,000 עסקאות"], [60, 50, 40, 30, 20].map((w) => [`${w}%`, n(Math.log(100) / Math.log(1 / (1 - w / 100)), 0), n(Math.log(1000) / Math.log(1 / (1 - w / 100)), 0)])) },
      { h: "שחק עם זה", html: "", play: { inputs: [["p", "אחוז הצלחה (%)", 48, 1], ["n", "עסקאות", 500, 50], ["r", "סיכון לעסקה (%)", 1, 0.25]],
          update(v) { const L = Math.log(v.n) / Math.log(1 / (1 - v.p / 100)); return [["רצף צפוי", n(L, 0)], ["ירידה ממנו", `${n(L * v.r, 1)}%`, "lx-neg"], ["רצף נדיר", n(L * 1.5, 0)]]; } } },
      { key: true, html: `<p><b>השורה התחתונה:</b> רצף הפסדים ארוך הוא חלק מהמתמטיקה של האסטרטגיה, לא סימן שהיא נשברה.</p>` },
    ] },

    { id: "sharpe", level: "תיק", title: "Sharpe וחיבור אסטרטגיות", steps: [
      { h: "Sharpe", html: `<div class="lx-f">Sharpe = ${frac("תשואה ממוצעת", "תנודתיות")} · √N<small>N = מספר התקופות בשנה</small></div><p>כמה תשואה מקבלים על כל יחידה של "רעד". 1 נחשב טוב, 2 מצוין. רוב קרנות הגידור מתחת ל־1.</p>` },
      { h: "הקסם של החיבור", html: "<p>שתי אסטרטגיות שלא קשורות זו לזו: כשאחת בירידה, השנייה לא בהכרח. הירידות לא מצטברות, אבל התשואות כן.</p>" },
      { h: "הנוסחה", html: `<div class="lx-f">S<sub>תיק</sub> = S · √${frac("k", "1 + (k − 1) · ρ")}<small>k אסטרטגיות עם Sharpe S · ρ = הקורלציה ביניהן</small></div><p>כש־ρ = 0: החוזק עולה כמו √k, וארבע אסטרטגיות לא קשורות מכפילות את ה־Sharpe.<br>כש־ρ = 1: זו אותה אסטרטגיה בתחפושת, ולא מרוויחים כלום.</p>` },
      { h: "שאלה", html: "", q: { ask: "יש לך 4 אסטרטגיות, כל אחת Sharpe 0.5, בלי קורלציה ביניהן. מה ה־Sharpe של התיק?", options: ["0.5", "1.0", "2.0"], answer: 1, explain: "0.5 × √4 = 1.0. אותן אסטרטגיות בינוניות, וביחד תיק טוב. ככה עובדים סוחרים שמחזיקים \"הרבה דברים קטנים ביחד\"." } },
      { h: "אצלנו", html: ex("Gotobi + RDM", "ין יפני בבוקר טוקיו, ונאסד״ק בניו יורק: כמעט לא קשורים.<br>ביחד: Sharpe של בערך 1.7–1.9, ו־15 מתוך 15 שנים חיוביות. את המטריצה רואים ב־Portfolio Lab.") },
      { h: "שחק עם זה", html: "", play: { inputs: [["s", "Sharpe של כל אחת", 0.7, 0.1], ["k", "כמה אסטרטגיות", 4, 1], ["r", "קורלציה ρ", 0.1, 0.05]],
          update(v) { const sp = v.s * Math.sqrt(v.k / (1 + (v.k - 1) * v.r)); return [["Sharpe התיק", n(sp, 2), "lx-pos"], ["פי כמה", `×${n(sp / v.s, 2)}`], ["אם ρ = 0", n(v.s * Math.sqrt(v.k), 2)]]; } } },
      { key: true, html: `<p><b>השורה התחתונה:</b> לא מחפשים יתרון ענק אחד. מחפשים עוד יתרון קטן שלא קשור למה שכבר יש.</p>` },
    ] },
  ];
}

const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* storage blocked */ } },
};

export function mountLearn(root, strategies, { start } = {}) {
  if (!document.getElementById("lx-style")) { const st = document.createElement("style"); st.id = "lx-style"; st.textContent = CSS; document.head.append(st); }
  const L = lessons(strategies || []);
  const prog = store.get("edge.learn.progress", {});             // lessonId -> furthest step index reached
  let cur = Math.max(0, L.findIndex((l) => l.id === start));
  root.innerHTML = `<div class="lx"><nav class="lx-nav" aria-label="שיעורים"></nav><article class="lx-body"></article></div>`;
  const nav = root.querySelector(".lx-nav"), body = root.querySelector(".lx-body");
  let advance = () => {};

  const paintNav = () => {
    let lvl = "";
    nav.innerHTML = L.map((l, i) => {
      const h = l.level !== lvl ? `<div class="lx-lvl">${l.level}</div>` : ""; lvl = l.level;
      const done = (prog[l.id] ?? -1) >= l.steps.length - 1;
      return `${h}<button data-i="${i}" aria-current="${i === cur}"><i class="${done ? "done" : ""}">${done ? "✓" : String(i + 1).padStart(2, "0")}</i><span>${l.title}</span></button>`;
    }).join("");
  };

  const stepHtml = (s, si) => `<section class="lx-step ${s.key ? "lx-key" : ""}" data-s="${si}">${s.h ? `<div class="lx-h">${s.h}</div>` : ""}${s.html || ""}
    ${s.q ? `<div class="lx-q"><p><b>${s.q.ask}</b></p><div class="lx-qa">${s.q.options.map((o, oi) => `<button type="button" data-o="${oi}">${o}</button>`).join("")}</div><div class="lx-fb" hidden></div></div>` : ""}
    ${s.play ? `<div class="lx-play"><div class="lx-row">${s.play.inputs.map(([k, l, v, st]) => `<label class="lx-in">${l}<input data-k="${k}" type="number" value="${v}" step="${st}"></label>`).join("")}</div><div class="lx-out"></div></div>` : ""}</section>`;

  const showLesson = (i) => {
    cur = i; const l = L[i];
    let shown = Math.min(prog[l.id] ?? 0, l.steps.length - 1);
    const answered = new Set();
    paintNav();
    body.innerHTML = `<div class="lx-top"><span class="lx-eyebrow">${l.level} · שיעור ${i + 1}</span><div class="lx-bar"><b></b></div><span class="lx-cnt"></span></div>
      <h2>${l.title}</h2><div class="lx-steps"></div><div class="lx-actions"></div>`;
    const steps = body.querySelector(".lx-steps"), actions = body.querySelector(".lx-actions");

    const paintActions = () => {
      const last = shown >= l.steps.length - 1, s = l.steps[shown], blocked = s.q && !answered.has(shown);
      body.querySelector(".lx-bar b").style.width = `${((shown + 1) / l.steps.length) * 100}%`;
      body.querySelector(".lx-cnt").textContent = `${shown + 1}/${l.steps.length}`;
      actions.innerHTML = last
        ? `${i < L.length - 1 ? `<button type="button" class="lx-go" data-a="next">לשיעור הבא: ${L[i + 1].title}</button>` : `<span class="lx-hint">סיימת את כל השיעורים.</span>`}<button type="button" class="lx-ghost" data-a="restart">להתחיל את השיעור מחדש</button>`
        : `<button type="button" class="lx-go" data-a="more" ${blocked ? "disabled" : ""}>המשך</button><span class="lx-hint">${blocked ? "בחר תשובה כדי להמשיך" : "או Enter"}</span>`;
    };

    const wire = (el, s, si) => {
      if (s.play) {
        const run = () => { const v = {}; el.querySelectorAll("input[data-k]").forEach((x) => (v[x.dataset.k] = +x.value)); el.querySelector(".lx-out").innerHTML = s.play.update(v).map(([a, b, c]) => `<div><span>${a}</span><b class="${c || ""}">${b}</b></div>`).join(""); };
        el.addEventListener("input", run); run();
      }
      if (s.q) el.querySelectorAll(".lx-qa button").forEach((b) => b.addEventListener("click", () => {
        const ok = +b.dataset.o === s.q.answer;
        el.querySelectorAll(".lx-qa button").forEach((x) => { x.disabled = true; if (+x.dataset.o === s.q.answer) x.classList.add("right"); });
        if (!ok) b.classList.add("wrong");
        const fb = el.querySelector(".lx-fb"); fb.hidden = false; fb.innerHTML = `${ok ? "✓ נכון. " : "לא בדיוק. "}${s.q.explain}`;
        answered.add(si); paintActions();
      }));
    };

    const add = (k, past) => {
      steps.insertAdjacentHTML("beforeend", stepHtml(l.steps[k], k));
      const el = steps.lastElementChild; wire(el, l.steps[k], k);
      if (past) {
        el.classList.add("past"); answered.add(k);
        if (l.steps[k].q) el.querySelector(`.lx-qa button[data-o="${l.steps[k].q.answer}"]`)?.click();   // show the explanation again
      }
      return el;
    };
    for (let k = 0; k <= shown; k++) add(k, k < shown);

    advance = () => {
      const s = l.steps[shown]; if (shown >= l.steps.length - 1 || (s.q && !answered.has(shown))) return;
      steps.lastElementChild.classList.add("past");
      shown++; prog[l.id] = Math.max(prog[l.id] ?? 0, shown); store.set("edge.learn.progress", prog);
      const el = add(shown, false);
      paintActions(); if (shown === l.steps.length - 1) paintNav();
      requestAnimationFrame(() => actions.scrollIntoView?.({ block: "nearest", behavior: "smooth" }));
    };

    actions.onclick = (e) => {
      const a = e.target.closest("button")?.dataset.a; if (!a) return;
      if (a === "more") advance();
      if (a === "next") { showLesson(i + 1); root.scrollIntoView?.({ block: "start", behavior: "smooth" }); }
      if (a === "restart") { prog[l.id] = 0; store.set("edge.learn.progress", prog); showLesson(i); }
    };
    paintActions();
  };

  nav.addEventListener("click", (e) => { const b = e.target.closest("button[data-i]"); if (b) showLesson(+b.dataset.i); });
  root.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.target.closest("input,button,textarea")) { e.preventDefault(); advance(); } });
  showLesson(cur);
  return { show: (id) => showLesson(Math.max(0, L.findIndex((l) => l.id === id))) };
}

/** Normalises the registry (data.json) or the app's /api/strategies rows into the shape the lessons use. */
export function normalise(rows) {
  return rows.map((s) => ({
    id: s.id, name: s.name, status: s.status, p: s.pRandom ?? s.p,
    win: s.winRate ?? s.win, avg: s.expectancy ?? s.avg, avgWin: s.avgWin ?? s.avg_win, avgLoss: s.avgLoss ?? s.avg_loss,
    sd: s.sd, n: s.n_trades ?? s.n, t: s.t ?? s.t_all, worstStreak: s.worstStreak ?? s.worst_streak,
    isAvg: s.isAvg ?? s.is_avg, oosAvg: s.oosAvg ?? s.oos_avg, mc: s.mc || null,
  }));
}
