// Edge Lab · Learn — quant trading lessons in Hebrew, built on the lab's own strategies.
// Self-contained (no imports): used by the local app (views/learn.js) and by the published Edge Lab page.
// mountLearn(root, strategies) — strategies: [{ id, name, status, win (%), avg (R), avgWin, avgLoss, sd, n, perYear, t, worstStreak }]
// RULE: when research changes a strategy, a gate or a method, update the lesson that explains it (see CLAUDE.md).

const CSS = `
.lx{--lx-fg:var(--fg,#f5f5f5);--lx-mut:var(--fg-2,var(--muted,#888));--lx-dim:var(--muted,#555);--lx-line:var(--border-soft,var(--line,#222));--lx-card:var(--card,var(--panel,#101010));--lx-acc:var(--accent,#e74747);
  direction:rtl;text-align:right;color:var(--lx-fg);display:grid;grid-template-columns:230px minmax(0,1fr);gap:28px;align-items:start;font-size:14.5px;line-height:1.75}
.lx *{box-sizing:border-box}
.lx-nav{position:sticky;top:var(--lx-top,16px);display:flex;flex-direction:column;gap:2px}
.lx-nav button{all:unset;cursor:pointer;display:grid;grid-template-columns:26px 1fr;gap:8px;align-items:center;padding:8px 10px;border-radius:8px;color:var(--lx-mut);font-size:13.5px}
.lx-nav button:hover{color:var(--lx-fg);background:rgba(127,127,127,.08)}
.lx-nav button[aria-current="true"]{color:var(--lx-fg);background:rgba(127,127,127,.13)}
.lx-nav button:focus-visible{outline:1.5px solid var(--lx-acc)}
.lx-nav i{font-style:normal;font-family:var(--mono,ui-monospace,monospace);font-size:11px;color:var(--lx-dim);text-align:center}
.lx-nav .lx-lvl{font-size:11px;color:var(--lx-dim);padding:12px 10px 4px}
.lx-body{min-width:0;max-width:760px}
.lx-eyebrow{font-size:12px;color:var(--lx-dim);font-family:var(--mono,ui-monospace,monospace);direction:ltr;text-align:right}
.lx h2{font-size:24px;font-weight:500;letter-spacing:-.02em;margin:4px 0 6px;line-height:1.3}
.lx .lx-why{color:var(--lx-mut);margin:0 0 22px;font-size:15px}
.lx h3{font-size:14px;font-weight:600;margin:26px 0 8px}
.lx p{margin:0 0 12px}
.lx ul{margin:0 0 12px;padding-right:20px;padding-left:0}
.lx li{margin:4px 0}
.lx b{font-weight:600}
.lx-f{direction:ltr;text-align:center;font-family:var(--mono,ui-monospace,monospace);font-size:17px;padding:20px 16px;margin:14px 0;border:1px solid var(--lx-line);border-radius:12px;background:rgba(127,127,127,.04);overflow-x:auto;white-space:nowrap}
.lx-f small{display:block;font-size:11.5px;color:var(--lx-dim);margin-top:8px;font-family:var(--sans,system-ui,sans-serif);white-space:normal;direction:rtl}
.lx-frac{display:inline-flex;flex-direction:column;vertical-align:middle;text-align:center;margin:0 4px}
.lx-frac>span:first-child{border-bottom:1px solid currentColor;padding:0 4px 2px}
.lx-frac>span:last-child{padding:2px 4px 0}
.lx-n{font-family:var(--mono,ui-monospace,monospace);direction:ltr;unicode-bidi:isolate;white-space:nowrap}
.lx-ex{border-right:2px solid var(--lx-acc);padding:10px 14px;margin:16px 0;background:rgba(231,71,71,.04);border-radius:8px 0 0 8px}
.lx-ex .lx-exh{font-size:11.5px;color:var(--lx-dim);margin-bottom:4px}
.lx-calc{border:1px solid var(--lx-line);border-radius:14px;padding:16px 18px;margin:18px 0;background:var(--lx-card)}
.lx-calc .lx-ch{font-size:12px;color:var(--lx-mut);margin-bottom:12px}
.lx-row{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end}
.lx-in{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--lx-mut);min-width:110px;flex:1}
.lx-in input{direction:ltr;font:inherit;font-family:var(--mono,ui-monospace,monospace);font-size:14px;color:var(--lx-fg);background:transparent;border:1px solid var(--lx-line);border-radius:8px;height:34px;padding:0 10px;width:100%}
.lx-in input:focus{outline:none;border-color:var(--lx-acc)}
.lx-out{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:1px;margin-top:14px;border:1px solid var(--lx-line);border-radius:10px;overflow:hidden;background:var(--lx-line)}
.lx-out div{background:var(--lx-card);padding:10px 12px}
.lx-out span{display:block;font-size:11.5px;color:var(--lx-dim)}
.lx-out b{font-family:var(--mono,ui-monospace,monospace);font-weight:500;font-size:17px;direction:ltr;display:block;text-align:right}
.lx-pos{color:var(--pos,var(--lx-fg))}.lx-neg{color:var(--lx-acc)}
.lx table.lx-tbl{width:100%;min-width:0;border-collapse:collapse;margin:10px 0 14px;font-size:13px}
.lx table.lx-tbl th{font-family:inherit;text-transform:none;letter-spacing:0;background:none;font-size:12px}
.lx-tbl th{font-weight:400;color:var(--lx-dim);text-align:right;padding:6px 8px;border-bottom:1px solid var(--lx-line)}
.lx-tbl td{padding:7px 8px;border-bottom:1px solid var(--lx-line);font-family:var(--mono,ui-monospace,monospace);direction:ltr;text-align:right}
.lx-tbl td:first-child{font-family:inherit;direction:rtl}
.lx-key{margin-top:26px;padding:14px 16px;border:1px solid var(--lx-line);border-radius:12px;font-size:13.5px}
.lx-key b{display:block;font-size:11.5px;color:var(--lx-dim);font-weight:400;margin-bottom:4px}
.lx-pager{display:flex;justify-content:space-between;margin-top:30px;gap:10px}
.lx-pager button{all:unset;cursor:pointer;font-size:13px;color:var(--lx-mut);padding:8px 12px;border:1px solid var(--lx-line);border-radius:8px}
.lx-pager button:hover{color:var(--lx-fg)}
@media (max-width:820px){.lx{grid-template-columns:1fr}.lx-nav{position:static;flex-direction:row;overflow-x:auto;gap:4px;padding-bottom:6px}.lx-nav button{grid-template-columns:auto;white-space:nowrap}.lx-nav i,.lx-nav .lx-lvl{display:none}}
`;

const n = (x, d = 2) => (x == null || !Number.isFinite(+x) ? "—" : (+x).toFixed(d));
const sg = (x, d = 3) => (x == null || !Number.isFinite(+x) ? "—" : `${x > 0 ? "+" : x < 0 ? "−" : ""}${Math.abs(x).toFixed(d)}`);
const N = (s) => `<span class="lx-n">${s}</span>`;
const frac = (a, b) => `<span class="lx-frac"><span>${a}</span><span>${b}</span></span>`;
const cls = (x) => (x > 0 ? "lx-pos" : x < 0 ? "lx-neg" : "");

/** Each lesson: id, level, title, why, html(S) → body, calc?: { html, update(root) } */
function lessons(S) {
  const by = (id) => S.find((s) => s.id === id) || {};
  const r10 = by("rdm10"), rdm = by("rdm"), gt = by("gotobi"), sp = by("sp");
  const streakPred = r10.win && r10.n ? Math.log(r10.n) / Math.log(1 / (1 - r10.win / 100)) : null;
  const nNeed = (s) => (s.avg > 0 && s.sd ? Math.ceil(((2 * s.sd) / s.avg) ** 2) : null);
  return [
    {
      id: "expectancy", level: "יסודות", title: "תוחלת: כמה עסקה ממוצעת שווה",
      why: "המספר הכי חשוב במסחר. לא אחוז ההצלחה, לא הרווח הגדול האחרון. כמה R אתה מרוויח בממוצע על כל עסקה.",
      html: () => `
        <h3>הנוסחה</h3>
        <div class="lx-f">E[R] = p · W − (1 − p) · L<small>p = אחוז ההצלחה (כשבר), W = רווח ממוצע בעסקה מנצחת ב־R, L = הפסד ממוצע בעסקה מפסידה ב־R</small></div>
        <p><b>R</b> הוא יחידת הסיכון: כמה תפסיד אם הסטופ נפגע. עסקה שהרוויחה פי 3 מהסיכון היא ${N("+3R")}, עסקה שנעצרה בסטופ היא ${N("−1R")}. מודדים ב־R ולא בדולרים כדי שתוכל להשוות אסטרטגיות עם גדלים שונים.</p>
        <p>אם E[R] חיובי, ככל שתסחר יותר, תרוויח יותר בממוצע. אם הוא שלילי, אין ניהול סיכונים שיציל אותך: זה רק יאט את ההפסד.</p>
        <div class="lx-ex"><div class="lx-exh">מהמעבדה שלנו · RDM 1:10</div>
          אחוז הצלחה ${N(n(r10.win, 1) + "%")}, רווח ממוצע ${N(sg(r10.avgWin, 2) + "R")}, הפסד ממוצע ${N(sg(r10.avgLoss, 2) + "R")}.<br>
          ${N(`E = ${n(r10.win / 100, 3)} × ${n(r10.avgWin, 2)} − ${n(1 - r10.win / 100, 3)} × ${n(-r10.avgLoss, 2)} = ${sg(r10.avg, 3)}R`)}<br>
          מפסידה 4 עסקאות מתוך 5, ובכל זאת אחת האסטרטגיות הכי חזקות שמצאנו.</div>
        <h3>נקודת האיזון</h3>
        <div class="lx-f">p* = ${frac("L", "W + L")} = ${frac("1", "1 + RR")}<small>אחוז ההצלחה המינימלי כדי לא להפסיד, כש־RR = W / L</small></div>
        <table class="lx-tbl"><thead><tr><th>יחס רווח־סיכון</th><th>הצלחה מינימלית</th></tr></thead><tbody>
          ${[0.25, 0.5, 1, 2, 3, 5, 10].map((rr) => `<tr><td>1:${rr}</td><td>${n(100 / (1 + rr), 1)}%</td></tr>`).join("")}</tbody></table>`,
      calc: {
        html: `<div class="lx-ch">מחשבון תוחלת</div><div class="lx-row">
          <label class="lx-in">אחוז הצלחה (%)<input data-k="p" type="number" value="48" step="0.5"></label>
          <label class="lx-in">רווח ממוצע (R)<input data-k="w" type="number" value="2" step="0.1"></label>
          <label class="lx-in">הפסד ממוצע (R)<input data-k="l" type="number" value="1" step="0.1"></label></div><div class="lx-out" data-out></div>`,
        update(v) { const p = v.p / 100, e = p * v.w - (1 - p) * v.l, be = v.l / (v.w + v.l); return [["תוחלת לעסקה", `${sg(e, 3)}R`, cls(e)], ["הצלחה מינימלית", `${n(be * 100, 1)}%`], ["על 100 עסקאות", `${sg(e * 100, 1)}R`, cls(e)]]; },
      },
      key: "אל תשאל מה אחוז ההצלחה. שאל מה התוחלת ב־R.",
    },
    {
      id: "winrate", level: "יסודות", title: "למה 98% הצלחה יכול להיות מלכודת",
      why: "אחוז הצלחה גבוה נשמע מעולה ונמכר טוב. בלי יחס רווח־סיכון הוא לא אומר כלום, ולפעמים הוא דגל אדום.",
      html: () => `
        <p>אפשר להגיע לכל אחוז הצלחה שרוצים: פשוט מקרבים את היעד ומרחיקים את הסטופ. היעד נפגע כמעט תמיד, והסטופ כמעט אף פעם, עד שהוא כן.</p>
        <table class="lx-tbl"><thead><tr><th>מבנה</th><th>הצלחה</th><th>רווח / הפסד</th><th>תוחלת</th></tr></thead><tbody>
          <tr><td>יעד זעיר, סטופ ענק</td><td>98%</td><td>+0.02R / −1R</td><td class="lx-neg">${sg(0.98 * 0.02 - 0.02 * 1, 4)}R</td></tr>
          <tr><td>יעד 1:1</td><td>55%</td><td>+1R / −1R</td><td class="lx-pos">${sg(0.55 - 0.45, 3)}R</td></tr>
          <tr><td>סוחר עם ניהול טוב</td><td>48%</td><td>+2R / −1R</td><td class="lx-pos">${sg(0.48 * 2 - 0.52, 3)}R</td></tr>
          <tr><td>RDM 1:10 (שלנו)</td><td>${n(r10.win, 1)}%</td><td>${sg(r10.avgWin, 2)}R / ${sg(r10.avgLoss, 2)}R</td><td class="lx-pos">${sg(r10.avg, 3)}R</td></tr></tbody></table>
        <p>שלוש שאלות לשאול כל מי שמוכר אחוז הצלחה גבוה:</p>
        <ul><li><b>מה היחס בין הרווח הממוצע להפסד הממוצע?</b> בלי זה, אחוז ההצלחה ריק.</li>
          <li><b>יש הכפלה אחרי הפסד (מרטינגייל)?</b> זה מייצר המון ניצחונות קטנים ופיצוץ אחד גדול.</li>
          <li><b>מה ההפסד הגרוע ביותר, ומה רצף ההפסדים הארוך?</b> תשובה של "אין" היא תשובה לא אמינה.</li></ul>
        <div class="lx-ex"><div class="lx-exh">מהמעבדה שלנו · AVP Zones</div>על הגרף ב־TradingView הסימנים נראו כמו 100% הצלחה, כי רואים בדיעבד רק את האזורים שעבדו. בבדיקה על 14 שנה עם עלויות: ${N(sg(by("avp").avg, 3) + "R")} לעסקה.</div>`,
      key: "אחוז הצלחה בלי יחס רווח־סיכון הוא מספר שיווקי, לא מדד ביצוע.",
    },
    {
      id: "sizing", level: "יסודות", title: "גודל פוזיציה ו־Kelly",
      why: "אותה אסטרטגיה בדיוק יכולה להכפיל חשבון או לפוצץ אותו. ההבדל הוא כמה אחוז מההון אתה מסכן בכל עסקה.",
      html: () => `
        <p>כשמסכנים אחוז קבוע מההון, למשל 1% לעסקה, כל ${N("1R")} שווה 1% מהחשבון. עסקה של ${N("+3R")} היא ${N("+3%")}.</p>
        <h3>נוסחת Kelly: הגודל שממקסם צמיחה</h3>
        <div class="lx-f">f* = p − ${frac("1 − p", "b")}<small>f* = החלק מההון לסכן בכל עסקה, p = הסתברות לניצחון, b = רווח ממוצע חלקי הפסד ממוצע</small></div>
        <p>Kelly המלא אגרסיבי מאוד: תנודות של עשרות אחוזים. סוחרים מקצועיים משתמשים ב<b>חצי Kelly או רבע Kelly</b>. מקבלים כ־75% מהצמיחה עם הרבה פחות כאב.</p>
        <div class="lx-ex"><div class="lx-exh">מהמעבדה שלנו · RDM 1:10</div>
          p = ${N(n(r10.win / 100, 3))}, b = ${N(n(r10.avgWin / -r10.avgLoss, 2))} → ${N(`f* = ${n(r10.win / 100 - (1 - r10.win / 100) / (r10.avgWin / -r10.avgLoss), 3)}`)}, כלומר כ־${N(n(100 * (r10.win / 100 - (1 - r10.win / 100) / (r10.avgWin / -r10.avgLoss)), 1) + "%")} לעסקה.<br>
          אבל עם רצף של ${N(r10.worstStreak)} הפסדים ברצף, גם רבע Kelly כואב. לכן ב־Monte Carlo בדקנו 1% לעסקה.</div>`,
      calc: {
        html: `<div class="lx-ch">מחשבון Kelly</div><div class="lx-row">
          <label class="lx-in">אחוז הצלחה (%)<input data-k="p" type="number" value="52" step="0.5"></label>
          <label class="lx-in">רווח ממוצע / הפסד ממוצע<input data-k="b" type="number" value="1.3" step="0.05"></label></div><div class="lx-out" data-out></div>`,
        update(v) { const p = v.p / 100, f = p - (1 - p) / v.b; return [["Kelly מלא", `${n(f * 100, 1)}%`, cls(f)], ["חצי Kelly", `${n(f * 50, 1)}%`, cls(f)], ["רבע Kelly", `${n(f * 25, 1)}%`, cls(f)]]; },
      },
      key: "Kelly שלילי אומר שאין יתרון: גודל הפוזיציה הנכון הוא אפס.",
    },
    {
      id: "tstat", level: "סטטיסטיקה", title: "מובהקות: האם זה יתרון או מזל",
      why: "כל אסטרטגיה מרוויחה לפעמים במקרה. ה־t-stat אומר כמה סביר שהרווח הממוצע שראית הוא מזל.",
      html: () => `
        <div class="lx-f">t = ${frac("R̄", "s / √n")}<small>R̄ = התוחלת שנמדדה, s = סטיית התקן של העסקאות (כמה הן מתפזרות), n = מספר העסקאות</small></div>
        <p>המכנה, ${N("s / √n")}, הוא ה"רעש" של הממוצע: כמה הוא היה זז אם היית מריץ את אותה אסטרטגיה בתקופה אחרת. t של 2 אומר שהתוחלת גדולה פי 2 מהרעש.</p>
        <ul><li><b>t ≈ 2</b>: בערך 5% סיכוי שזה מזל, אם זה המבחן היחיד שהרצת.</li><li><b>t ≥ 3</b>: הרף שלנו במפעלים, כי הרצנו המון מבחנים (שיעור הבא).</li></ul>
        <h3>כמה עסקאות צריך כדי להוכיח?</h3>
        <div class="lx-f">n ≈ (${frac("2 · s", "R̄")})²<small>מספר העסקאות שצריך כדי להגיע ל־t = 2</small></div>
        <div class="lx-ex"><div class="lx-exh">מהמעבדה שלנו</div>
          Gotobi: R̄ = ${N(sg(gt.avg, 3))}, s = ${N(n(gt.sd, 2))} → צריך כ־${N(nNeed(gt) ?? "—")} עסקאות. יש ${N(gt.n ?? "—")}, ולכן t = ${N(n(gt.t, 2))}.<br>
          RDM 1:10: R̄ = ${N(sg(r10.avg, 3))}, s = ${N(n(r10.sd, 2))} → צריך כ־${N(nNeed(r10) ?? "—")} עסקאות. הפיזור הגדול של 1:10 דורש הרבה יותר הוכחות.</div>`,
      calc: {
        html: `<div class="lx-ch">כמה עסקאות צריך</div><div class="lx-row">
          <label class="lx-in">תוחלת R̄ (R)<input data-k="m" type="number" value="0.15" step="0.01"></label>
          <label class="lx-in">סטיית תקן s (R)<input data-k="s" type="number" value="1.5" step="0.1"></label>
          <label class="lx-in">עסקאות שיש לך<input data-k="n" type="number" value="200" step="10"></label></div><div class="lx-out" data-out></div>`,
        update(v) { const t = v.m / (v.s / Math.sqrt(v.n)); return [["t-stat עכשיו", n(t, 2), t >= 2 ? "lx-pos" : "lx-neg"], ["עסקאות ל־t=2", n(((2 * v.s) / v.m) ** 2, 0)], ["עסקאות ל־t=3", n(((3 * v.s) / v.m) ** 2, 0)]]; },
      },
      key: "יתרון קטן עם פיזור גדול דורש מאות ואלפי עסקאות. חודש אחד מוכיח מעט מאוד.",
    },
    {
      id: "multiple", level: "סטטיסטיקה", title: "בדיקות מרובות ו־Overfitting",
      why: "אם בודקים מספיק רעיונות, חלק ייראו מעולה במקרה. זו הסיבה מספר אחת שאסטרטגיות 'מושלמות' נכשלות בלייב.",
      html: () => `
        <div class="lx-f">E[false positives] = N · α<small>N = מספר המבחנים, α = הסיכוי למזל בכל מבחן (למשל 5%)</small></div>
        <p>בודקים 1,000 אסטרטגיות חסרות ערך עם רף של 5%, ובממוצע כ־50 מהן "עוברות". אם בוחרים את הטובה מהן, בחרת את בעלת המזל הגדול ביותר.</p>
        <h3>שלוש הגנות שאנחנו משתמשים בהן</h3>
        <ul><li><b>רף גבוה יותר</b> (Bonferroni): מחלקים את α במספר המבחנים, ולכן t ≥ 3 ולא 2.</li>
          <li><b>כמה שלבים</b>: עובר ב־2012–17, ואז ב־2018–21, ורק אז מסתכלים פעם אחת על 2022–26.</li>
          <li><b>מפעל פלסבו</b>: מריצים את אותו חיפוש בדיוק על נתונים שערבבנו. מה ששווה משהו זה רק כמה <b>יותר</b> מהפלסבו יצא.</li></ul>
        <div class="lx-ex"><div class="lx-exh">מהמעבדה שלנו · מפעל Layers</div>
          בדקנו ${N("13,271,040")} אסטרטגיות של גאפים רב־שכבתיות. עברו 17, אבל בגרסה האקראית עברו 22, ורק אחת מה־17 הרוויחה ב־2022–26. כלומר כל ה"מנצחות" היו מזל.<br>
          במפעל התיאוריות הראשון יצאו ${N("142")} מול ${N("2")} בפלסבו. מתוכו נולד RDM.</div>`,
      key: "השאלה היא לא 'כמה עברו', אלא 'כמה עברו יותר מהאקראי'.",
    },
    {
      id: "placebo", level: "סטטיסטיקה", title: "המבחן מול אקראי (Placebo)",
      why: "הדרך הכי ישירה לדעת אם הכלל שלך עושה משהו: להשוות אותו לגרסה שבורה של עצמו.",
      html: () => `
        <div class="lx-f">p = ${frac("#{ runs random ≥ real }", "#{ runs random }")}<small>החלק של הריצות האקראיות שהצליחו לפחות כמו האסטרטגיה האמיתית</small></div>
        <p>בונים "תאום" שזהה לאסטרטגיה בכל דבר, חוץ מהחלק שאמור להיות היתרון:</p>
        <ul><li><b>שעונים מוזזים</b>: אם הסוד הוא שעה מסוימת, מזיזים את כל השעות.</li>
          <li><b>ימים מעורבבים</b>: אם הסוד הוא תאריך, מגרילים תאריכים.</li>
          <li><b>כיוון אקראי</b>: אם הסוד הוא הכיוון, מגרילים לונג או שורט.</li>
          <li><b>אזורים מוזזים</b>: אם הסוד הוא רמת מחיר, מזיזים את הרמות.</li></ul>
        <p>מריצים את התאום אלפי פעמים. אם 30% מהריצות האקראיות הרוויחו כמוך, p = 0.30, והכלל שלך לא שווה כלום.</p>
        <div class="lx-ex"><div class="lx-exh">מהמעבדה שלנו</div>
          Gotobi: p ${N(gt.p ?? "—")} · RDM: p ${N(rdm.p ?? "—")} · RDM 1:10: p ${N(r10.p ?? "—")} · AVP Zones: p ${N(by("avp").p ?? "—")}<br>
          ב־AVP, אזורים אקראיים הרוויחו ב־42% מהמקרים כמו האזורים "האמיתיים".</div>
        <p><b>שים לב לנקודה עדינה:</b> באסטרטגיות עם יעד גדול, כמו 1:10, גם כיוון אקראי מרוויח בממוצע, כי ההפסדים קטנים והרווחים גדולים. לכן משווים לפלסבו ולא לאפס. ב־RDM 1:10 החציון של הפלסבו היה ${N("+0.16R")}, והאמיתי עמד על ${N(sg(r10.avg, 2) + "R")} ומעל.</p>`,
      key: "אם גרסה אקראית של הרעיון עושה אותו דבר, אין לך רעיון.",
    },
    {
      id: "oos", level: "סטטיסטיקה", title: "In-sample ו־Out-of-sample",
      why: "כל אסטרטגיה מכוילת נראית טוב על הנתונים שעליהם כיילו אותה. האמת נמדדת רק על נתונים שהיא לא ראתה.",
      html: () => `
        <ul><li><b>In-sample (2012–19)</b>: כאן מותר לחפש, לכייל ולבחור.</li>
          <li><b>Out-of-sample (2020–26)</b>: כאן מסתכלים <b>פעם אחת</b>. אם חוזרים לכייל אחרי שהסתכלת, הנתונים האלה כבר "נשרפו".</li></ul>
        <div class="lx-f">degradation = ${frac("R̄ out − R̄ in", "|R̄ in|")}<small>כמה התוחלת נשחקה כשעברנו לנתונים חדשים</small></div>
        <table class="lx-tbl"><thead><tr><th>אסטרטגיה</th><th>2012–19</th><th>2020–26</th></tr></thead><tbody>
          ${[gt, rdm, r10, sp].filter((s) => s.name).map((s) => `<tr><td>${s.name}</td><td class="${cls(s.isAvg)}">${sg(s.isAvg, 3)}</td><td class="${cls(s.oosAvg)}">${sg(s.oosAvg, 3)}</td></tr>`).join("")}</tbody></table>
        <p>שים לב ש־RDM 1:10 היה <b>שלילי</b> ב־2012–19 אחרי עלויות, והתחזק אחרי 2020. זו סיבה להיזהר: חלק מהכוח שלו תלוי בתנודתיות הגבוהה של השנים האחרונות.</p>`,
      key: "תוצאה שנראית מושלמת על כל הנתונים, בלי חלוקה, היא כמעט תמיד overfitting.",
    },
    {
      id: "montecarlo", level: "סיכון", title: "Monte Carlo: אלפי עתידים אפשריים",
      why: "ההיסטוריה שקרתה היא רק סדר אחד של העסקאות. Monte Carlo מראה מה עוד היה יכול לקרות עם אותן עסקאות.",
      html: () => `
        <p>לוקחים את העסקאות האמיתיות ושולפים מהן באקראי (עם החזרה) "שנה" חדשה. חוזרים על זה 5,000 פעמים ומקבלים 5,000 שנים אפשריות.</p>
        <div class="lx-f">Equity<sub>k</sub> = Capital + Σ<sub>i≤k</sub> R<sub>i</sub> · risk<small>R<sub>i</sub> נשלף באקראי מתוך העסקאות האמיתיות</small></div>
        <ul><li><b>חציון</b>: השנה ה"רגילה".</li><li><b>אחוזון 5</b>: שנה רעה, שתקרה בערך פעם ב־20 שנה.</li>
          <li><b>ירידה באחוזון 95</b>: הירידה שכדאי להיערך אליה.</li><li><b>סיכון לפשיטת רגל</b>: החלק מהעתידים שבהם החשבון ירד מתחת לסף.</li></ul>
        <div class="lx-ex"><div class="lx-exh">מהמעבדה שלנו</div>ב־Gotobi כ־95% מהשנים המדומות חיוביות, וב־RDM 1:10 רק כ־70%. התוחלת של 1:10 גבוהה יותר, אבל הדרך הרבה יותר קשה.</div>
        <p><b>המגבלה:</b> השליפה בלתי תלויה, אז רצפים ושינויי משטר שוק לא נשמרים. מי שרוצה זהירות נוספת משתמש ב־block bootstrap, ששולף רצפים של עסקאות.</p>`,
      key: "אל תשאל רק 'כמה ארוויח'. שאל 'מה הירידה שאצטרך לשרוד בדרך'.",
    },
    {
      id: "streaks", level: "סיכון", title: "רצפי הפסדים: כמה זה צפוי",
      why: "רוב הסוחרים זונחים אסטרטגיה טובה באמצע רצף הפסדים רגיל לחלוטין. אם יודעים מראש כמה רצף צפוי, לא נבהלים.",
      html: () => `
        <div class="lx-f">L<sub>max</sub> ≈ ${frac("ln(n)", "ln(1 / (1 − p))")}<small>אורך הרצף הארוך ביותר שצפוי ב־n עסקאות, כש־p הוא אחוז ההצלחה</small></div>
        <div class="lx-ex"><div class="lx-exh">מהמעבדה שלנו · RDM 1:10</div>
          n = ${N(r10.n ?? "—")}, p = ${N(n(r10.win / 100, 3))} → הנוסחה צופה רצף של כ־${N(n(streakPred, 0))} הפסדים. בפועל: ${N(r10.worstStreak ?? "—")}.<br>
          מי שלא ידע את זה היה עוצר אחרי 15 הפסדים, ומפספס את הרווח.</div>
        <table class="lx-tbl"><thead><tr><th>אחוז הצלחה</th><th>100 עסקאות</th><th>1,000 עסקאות</th></tr></thead><tbody>
          ${[60, 50, 40, 30, 20].map((w) => `<tr><td>${w}%</td><td>${n(Math.log(100) / Math.log(1 / (1 - w / 100)), 0)}</td><td>${n(Math.log(1000) / Math.log(1 / (1 - w / 100)), 0)}</td></tr>`).join("")}</tbody></table>`,
      calc: {
        html: `<div class="lx-ch">איזה רצף לצפות</div><div class="lx-row">
          <label class="lx-in">אחוז הצלחה (%)<input data-k="p" type="number" value="48" step="1"></label>
          <label class="lx-in">מספר עסקאות<input data-k="n" type="number" value="500" step="50"></label>
          <label class="lx-in">סיכון לעסקה (%)<input data-k="r" type="number" value="1" step="0.25"></label></div><div class="lx-out" data-out></div>`,
        update(v) { const L = Math.log(v.n) / Math.log(1 / (1 - v.p / 100)); return [["רצף צפוי", n(L, 0)], ["ירידה מהרצף", `${n(L * v.r, 1)}%`, "lx-neg"], ["רצף כפול (נדיר)", n(L * 1.5, 0)]]; },
      },
      key: "רצף הפסדים ארוך הוא חלק מהמתמטיקה של האסטרטגיה, לא סימן שהיא נשברה.",
    },
    {
      id: "sharpe", level: "תיק", title: "Sharpe וחיבור אסטרטגיות",
      why: "יתרון גדול נבנה מכמה יתרונות קטנים שלא קשורים זה לזה. זו המתמטיקה שמאחורי הסוחרים שמחזיקים 'כמה דברים ביחד'.",
      html: () => `
        <div class="lx-f">Sharpe = ${frac("R̄", "σ")} · √N<small>תשואה ממוצעת חלקי תנודתיות, כפול שורש מספר התקופות בשנה</small></div>
        <p>Sharpe של 1 נחשב טוב, ו־2 נחשב מצוין. רוב קרנות הגידור מתחת ל־1.</p>
        <h3>מה קורה כשמחברים אסטרטגיות</h3>
        <div class="lx-f">S<sub>p</sub> = S · √(${frac("k", "1 + (k − 1) · ρ")})<small>k אסטרטגיות עם אותו Sharpe S וקורלציה ρ ביניהן</small></div>
        <ul><li>כש־ρ = 0 (לא קשורות), החוזק עולה כמו √k: ארבע אסטרטגיות מכפילות את ה־Sharpe.</li>
          <li>כש־ρ = 1 (אותה אסטרטגיה בתחפושת), לא מרוויחים כלום מהחיבור.</li></ul>
        <div class="lx-ex"><div class="lx-exh">מהמעבדה שלנו</div>Gotobi (ין יפני, בוקר טוקיו) ו־RDM (נאסד״ק, ניו יורק) כמעט לא קשורים. כל אחד לבד חזק, וביחד הם נותנים Sharpe של כ־1.7–1.9 ו־15 מתוך 15 שנים חיוביות. את המטריצה המלאה רואים ב־Portfolio Lab.</div>`,
      calc: {
        html: `<div class="lx-ch">כמה שווה עוד אסטרטגיה</div><div class="lx-row">
          <label class="lx-in">Sharpe של כל אחת<input data-k="s" type="number" value="0.7" step="0.1"></label>
          <label class="lx-in">מספר אסטרטגיות k<input data-k="k" type="number" value="4" step="1" min="1"></label>
          <label class="lx-in">קורלציה ρ<input data-k="r" type="number" value="0.1" step="0.05" min="-0.3" max="1"></label></div><div class="lx-out" data-out></div>`,
        update(v) { const sp = v.s * Math.sqrt(v.k / (1 + (v.k - 1) * v.r)); return [["Sharpe התיק", n(sp, 2), "lx-pos"], ["פי כמה מאחת", `×${n(sp / v.s, 2)}`], ["אם ρ = 0", n(v.s * Math.sqrt(v.k), 2)]]; },
      },
      key: "החיפוש הוא לא אחרי היתרון הגדול. הוא אחרי עוד יתרון קטן שלא קשור למה שכבר יש לך.",
    },
  ];
}

export function mountLearn(root, strategies, { start } = {}) {
  if (!document.getElementById("lx-style")) { const st = document.createElement("style"); st.id = "lx-style"; st.textContent = CSS; document.head.append(st); }
  const L = lessons(strategies || []);
  let cur = Math.max(0, L.findIndex((l) => l.id === start));
  root.innerHTML = `<div class="lx"><nav class="lx-nav" aria-label="שיעורים"></nav><article class="lx-body" aria-live="polite"></article></div>`;
  const nav = root.querySelector(".lx-nav"), body = root.querySelector(".lx-body");
  let lvl = "";
  nav.innerHTML = L.map((l, i) => { const h = l.level !== lvl ? `<div class="lx-lvl">${l.level}</div>` : ""; lvl = l.level; return `${h}<button data-i="${i}"><i>${String(i + 1).padStart(2, "0")}</i><span>${l.title}</span></button>`; }).join("");
  const show = (i) => {
    cur = i; const l = L[i];
    nav.querySelectorAll("button").forEach((b) => b.setAttribute("aria-current", +b.dataset.i === i));
    body.innerHTML = `<div class="lx-eyebrow">${l.level} · ${i + 1}/${L.length}</div><h2>${l.title}</h2><p class="lx-why">${l.why}</p>${l.html()}
      ${l.calc ? `<div class="lx-calc">${l.calc.html}</div>` : ""}<div class="lx-key"><b>השורה התחתונה</b>${l.key}</div>
      <div class="lx-pager">${i > 0 ? `<button data-go="${i - 1}">→ ${L[i - 1].title}</button>` : "<span></span>"}${i < L.length - 1 ? `<button data-go="${i + 1}">${L[i + 1].title} ←</button>` : ""}</div>`;
    if (l.calc) {
      const box = body.querySelector(".lx-calc"), out = box.querySelector("[data-out]");
      const run = () => { const v = {}; box.querySelectorAll("input[data-k]").forEach((x) => (v[x.dataset.k] = +x.value)); out.innerHTML = l.calc.update(v).map(([a, b, c]) => `<div><span>${a}</span><b class="${c || ""}">${b}</b></div>`).join(""); };
      box.addEventListener("input", run); run();
    }
    body.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => { show(+b.dataset.go); root.scrollIntoView?.({ block: "start", behavior: "smooth" }); }));
  };
  nav.addEventListener("click", (e) => { const b = e.target.closest("button[data-i]"); if (b) show(+b.dataset.i); });
  show(cur);
  return { show: (id) => show(Math.max(0, L.findIndex((l) => l.id === id))) };
}

/** Normalises the registry (data.json) or the app's /api/strategies rows into the shape the lessons use. */
export function normalise(rows) {
  return rows.map((s) => ({
    id: s.id, name: s.name, status: s.status, p: s.pRandom ?? s.p,
    win: s.winRate ?? s.win, avg: s.expectancy ?? s.avg, avgWin: s.avgWin ?? s.avg_win, avgLoss: s.avgLoss ?? s.avg_loss,
    sd: s.sd, n: s.n_trades ?? s.n, t: s.t ?? s.t_all, worstStreak: s.worstStreak ?? s.worst_streak,
    isAvg: s.isAvg ?? s.is_avg, oosAvg: s.oosAvg ?? s.oos_avg,
  }));
}
