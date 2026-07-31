/* ============================================================
   BIG BRANDS — smart shopping assistant (client-side, no backend)
   Understands Hebrew intent, recommends from the live catalog,
   answers FAQ, and hands off to WhatsApp.
   ============================================================ */
(function () {
  "use strict";
  const WA_PHONE = "972508808076"; // TODO: real WhatsApp number
  const ils = (n) => Number(n).toLocaleString("he-IL") + " ₪";
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const products = () => (window.Store ? Store.getProducts() : (window.SITE_DATA ? SITE_DATA.products : []));

  /* ---------- classification helpers ---------- */
  function ptype(p) {
    if (p.category === "מסכים") return "monitor";
    if (p.category === "אביזרים") return "accessory";
    if (p.category === "באנדלים") return "bundle";
    if (/ThinkCentre|EliteDesk|נייח|Mini|M900|M93p/i.test(p.name)) return "desktop";
    return "laptop";
  }

  /* ---------- intent parsing ---------- */
  function parse(t) {
    const s = " " + t.toLowerCase().replace(/[,]/g, "") + " ";
    const it = { raw: t };
    const bud = t.replace(/,/g, "").match(/(?:עד|תקציב|מקסימום|בסביבות|במסגרת|לא יותר מ)\D{0,4}(\d{3,6})/) || t.replace(/,/g, "").match(/(\d{3,6})\s*(?:₪|שקל|שח)/) || (t.replace(/,/g,"").match(/^\s*(\d{3,6})\s*$/));
    if (bud) it.budget = parseInt(bud[1]);
    if (/עסק|משרד|עבוד|חברה|ארגון/.test(s)) it.use = "business";
    else if (/גיימינג|גיימ|משחק|gaming/.test(s)) it.use = "gaming";
    else if (/סטודנט|לימוד|בית ספר|אוניברסיט/.test(s)) it.use = "student";
    else if (/בית|ביתי|גלישה|נטפליקס|יומיום/.test(s)) it.use = "home";
    else if (/עריכ|וידאו|גרפי|render|כבד|תובעני|פוטושופ/.test(s)) it.use = "heavy";
    if (/נייד|לפטופ|laptop|מחברת/.test(s)) it.type = "laptop";
    else if (/נייח|דסקטופ|מגדל|desktop|tiny|מיני/.test(s)) it.type = "desktop";
    else if (/מסך|מוניטור|monitor|צג/.test(s)) it.type = "monitor";
    else if (/מקלדת|עכבר|כבל|מטען|אופיס|office|אביזר/.test(s)) it.type = "accessory";
    else if (/באנדל|חביל|מארז|bundle/.test(s)) it.type = "bundle";
    if (/יד ?שני|מחודש|משומש|רפרביש|refurb/.test(s)) it.cond = "used";
    else if (/חדש לגמרי|חדשים|new/.test(s)) it.cond = "new";
    if (/לנובו|lenovo|thinkpad|thinkcentre/.test(s)) it.brand = "Lenovo";
    else if (/\bhp\b|elitedesk|probook|היו?לט/.test(s)) it.brand = "HP";
    else if (/דל|dell|latitude/.test(s)) it.brand = "Dell";
    const specs = [];
    if (/32 ?gb|32 ?ג/.test(s)) specs.push("32GB");
    else if (/16 ?gb|16 ?ג/.test(s)) specs.push("16GB");
    if (/i7|איי? ?7/.test(s)) specs.push("i7");
    if (/512/.test(s)) specs.push("512GB");
    if (/1 ?tb|1 ?טרה/.test(s)) specs.push("1TB");
    if (specs.length) it.specs = specs;

    // FAQ intents
    if (/משלוח|מתי מגיע|זמן אספק|שילוח/.test(s)) it.faq = "shipping";
    else if (/אחריות|warranty|תיקון|קלקל/.test(s)) it.faq = "warranty";
    else if (/תשלום|אשראי|קרדיט|פייבוקס|ביט|תשלומים|payment/.test(s)) it.faq = "payment";
    else if (/החזר|ביטול|לא מרוצה|return|refund/.test(s)) it.faq = "returns";
    else if (/מה זה יד|למה יד שני|מחודש זה|refurb\?/.test(s)) it.faq = "refurb";
    else if (/נציג|אנוש|טלפון|וואטסאפ|whatsapp|לדבר עם|צור קשר/.test(s)) it.faq = "contact";
    if (/^(שלום|היי|הי|הלו|אהלן|בוקר טוב|ערב טוב|hello|hey|hi)\b/.test(t.trim().toLowerCase())) it.greet = true;
    if (/תודה|thanks|יופי|מעולה|סבבה/.test(s)) it.thanks = true;
    return it;
  }

  function recommend(it) {
    let list = products().slice();
    if (it.type) list = list.filter((p) => it.type === "used" ? true : ptype(p) === it.type);
    if (it.cond === "used") list = list.filter((p) => p.category === "יד שנייה");
    if (it.cond === "new") list = list.filter((p) => p.category === "מחשבים חדשים");
    if (it.brand) list = list.filter((p) => p.brand === it.brand);
    if (it.budget) list = list.filter((p) => p.price <= it.budget);
    if (it.specs) list = list.filter((p) => it.specs.every((sp) => (p.specs || "").toUpperCase().includes(sp.toUpperCase())));
    if (it.use === "business" || it.use === "student" || it.use === "home")
      list = list.filter((p) => ptype(p) === "laptop" || ptype(p) === "desktop");
    if (it.use === "heavy") list = list.filter((p) => /i7|32GB|16GB/i.test(p.specs || ""));
    list.sort((a, b) => a.price - b.price);
    return list;
  }

  /* ---------- UI ---------- */
  let root, body, awaiting = null, greeted = false;
  const logo = "assets/logo.png";

  function build() {
    root = document.createElement("div");
    root.innerHTML = `
      <button class="cbot-launch" id="cbotLaunch" aria-label="פתח עוזר קנייה חכם">
        <span class="cbot-spark"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 4.8L19 9.5l-4.1 2.9L16 18l-4-2.7L8 18l1.1-5.6L5 9.5l5.1-1.7z"/></svg></span>
        <span class="cbot-label">עוזר חכם</span>
        <span class="cbot-dot"></span>
      </button>
      <section class="cbot" id="cbot" role="dialog" aria-label="עוזר קנייה BIG BRANDS">
        <header class="cbot-head">
          <span class="cbot-ava"><img src="${logo}" alt="BIG BRANDS" onerror="this.style.display='none'"/></span>
          <div class="cbot-htxt"><b>העוזר החכם של BIG BRANDS</b><span>מקוון · משיב תוך שניות</span></div>
          <button class="cbot-x" id="cbotClose" aria-label="סגור"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg></button>
        </header>
        <div class="cbot-body" id="cbotBody"></div>
        <footer class="cbot-foot">
          <form class="cbot-inwrap" id="cbotForm">
            <input class="cbot-in" id="cbotIn" placeholder="ספרו לי מה אתם מחפשים…" autocomplete="off" aria-label="הודעה" />
            <button class="cbot-send" type="submit" aria-label="שליחה"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/></svg></button>
          </form>
          <div class="cbot-hint">מופעל על ידי BIG BRANDS · המלצות מהמלאי בזמן אמת</div>
        </footer>
      </section>`;
    document.body.appendChild(root);
    body = root.querySelector("#cbotBody");
    root.querySelector("#cbotLaunch").addEventListener("click", open);
    root.querySelector("#cbotClose").addEventListener("click", close);
    root.querySelector("#cbotForm").addEventListener("submit", (e) => { e.preventDefault(); const v = root.querySelector("#cbotIn").value.trim(); if (v) { userSay(v); root.querySelector("#cbotIn").value = ""; } });
  }

  function open() { document.documentElement.classList.add("cbot-open"); if (!greeted) { greeted = true; setTimeout(greet, 250); } setTimeout(() => root.querySelector("#cbotIn").focus(), 400); }
  function close() { document.documentElement.classList.remove("cbot-open"); }
  const scroll = () => { body.scrollTop = body.scrollHeight; };

  function botBubble(html) {
    const row = document.createElement("div"); row.className = "cbot-row bot";
    row.innerHTML = `<span class="cbot-mini"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 4.8L19 9.5l-4.1 2.9L16 18l-4-2.7L8 18l1.1-5.6L5 9.5l5.1-1.7z"/></svg></span><div class="cbot-bub">${html}</div>`;
    body.appendChild(row); scroll();
  }
  function userBubble(text) {
    const row = document.createElement("div"); row.className = "cbot-row user";
    row.innerHTML = `<div class="cbot-bub">${esc(text)}</div>`;
    body.appendChild(row); scroll();
  }
  function chips(arr) {
    const wrap = document.createElement("div"); wrap.className = "cbot-chips";
    arr.forEach((c) => { const b = document.createElement("button"); b.className = "cbot-chip"; b.textContent = c; b.addEventListener("click", () => userSay(c)); wrap.appendChild(b); });
    body.appendChild(wrap); scroll();
  }
  function productCard(p) {
    const a = document.createElement("a"); a.className = "cbot-prod"; a.href = "product.html?id=" + encodeURIComponent(p.id);
    a.innerHTML = `<img class="cbot-pimg" src="${esc(p.image || "")}" alt="" onerror="this.style.visibility='hidden'"/>
      <div class="cbot-pinfo"><div class="cbot-pname">${esc(p.name)}</div><div class="cbot-pprice">${ils(p.price)}${p.wasPrice ? ` <span style="color:var(--text-faint);font-weight:600;font-size:.8em;text-decoration:line-through">${ils(p.wasPrice)}</span>` : ""}</div></div>`;
    body.appendChild(a); scroll();
  }
  function typing() {
    const row = document.createElement("div"); row.className = "cbot-row bot"; row.id = "cbotTyping";
    row.innerHTML = `<span class="cbot-mini"></span><div class="cbot-bub cbot-typing"><i></i><i></i><i></i></div>`;
    body.appendChild(row); scroll(); return row;
  }
  function botSay(fn, delay) {
    const t = typing();
    setTimeout(() => { t.remove(); fn(); }, delay || 600 + Math.random() * 500);
  }
  const waLink = (msg) => `https://wa.me/${WA_PHONE}?text=${encodeURIComponent(msg)}`;

  function greet() {
    botSay(() => {
      botBubble(`שלום 👋 אני העוזר החכם של <b>BIG BRANDS</b>. אשמח לעזור לכם למצוא בדיוק את מה שאתם צריכים.`);
      setTimeout(() => botSay(() => {
        botBubble(`מה מעניין אתכם? אפשר גם פשוט לכתוב לי (למשל: "מחשב נייד לעסק עד 1500").`);
        chips(["המלצה לפי תקציב 💰", "מחשב לעסק 💼", "יד שנייה משתלם ♻️", "משלוח ואחריות 🚚", "דבר עם נציג 💬"]);
      }, 500), 500);
    }, 500);
  }

  function resultsFor(it, introText) {
    const list = recommend(it);
    botSay(() => {
      if (!list.length) {
        if (it.use === "gaming") {
          botBubble(`כרגע אין מחשבי גיימינג מוכנים במלאי — אבל אנחנו <b>מרכיבים מחשב גיימינג מותאם</b> לפי התקציב שלכם! רוצים שנציג יחזור אליכם?`);
        } else {
          botBubble(`לא מצאתי התאמה מדויקת 😅 אבל יש לנו עוד הרבה — אפשר להרחיב תקציב או לבחור קטגוריה:`);
          chips(["כל המוצרים 🗂️", "יד שנייה ♻️", "דבר עם נציג 💬"]);
          return;
        }
        chips(["דבר עם נציג 💬", "כל המוצרים 🗂️"]);
        return;
      }
      botBubble(introText || `הנה ${Math.min(list.length, 3)} המלצות מעולות בשבילכם:`);
      list.slice(0, 3).forEach(productCard);
      const extra = ["דבר עם נציג 💬"];
      if (list.length > 3) extra.unshift("עוד אפשרויות ➕");
      chips(extra);
      window.__cbotMore = list.slice(3);
    });
  }

  function faqReply(kind) {
    const map = {
      shipping: `🚚 <b>משלוח</b>: אספקה עד 3 ימי עסקים לכל הארץ. יש גם איסוף עצמי בתיאום. רוצים לבדוק זמינות למוצר מסוים?`,
      warranty: `🛡️ <b>אחריות</b>: אחריות יצרן מלאה למוצרים חדשים, ואחריות BIG BRANDS למוצרי יד-שנייה. אפשר גם להרחיב אחריות. על איזה מוצר תרצו פרטים?`,
      payment: `💳 <b>תשלום</b>: כרטיסי אשראי, Bit ו-PayBox, ואפשרות תשלומים. רוצים שאבנה לכם הצעת מחיר?`,
      returns: `↩️ <b>החזרות</b>: 14 ימי החזרה מלאים ללא שאלות, בהתאם לחוק הגנת הצרכן.`,
      refurb: `♻️ <b>יד שנייה / מחודש</b>: מחשבים עסקיים איכותיים שעברו בדיקה, ניקוי והתקנה מחדש — ביצועים מצוינים במחיר משתלם בהרבה, עם אחריות. רוצים לראות דגמים?`,
      contact: `💬 אשמח לחבר אתכם לנציג אנושי בוואטסאפ — <a href="${waLink("היי, הגעתי מהאתר ואשמח לעזרה 🙂")}" target="_blank" rel="noopener" style="color:var(--blue);font-weight:700">לחצו כאן לפתיחת שיחה</a>.`,
    };
    botSay(() => {
      botBubble(map[kind]);
      if (kind === "refurb") chips(["יד שנייה ♻️", "מחשב לעסק 💼"]);
      else if (kind !== "contact") chips(["המלצה לפי תקציב 💰", "דבר עם נציג 💬"]);
    });
  }

  function userSay(text) {
    userBubble(text);
    const t = text.replace(/[💰💼♻️🚚💬🗂️➕🙂👋]/g, "").trim();

    if (awaiting === "budget") {
      const m = t.replace(/,/g, "").match(/(\d{3,6})/);
      awaiting = null;
      if (m) { resultsFor({ budget: parseInt(m[1]) }, `מצוין! הנה הבחירות המשתלמות ביותר עד ${ils(parseInt(m[1]))}:`); return; }
    }

    const it = parse(t);

    if (/^עוד אפשרויות/.test(t) && window.__cbotMore && window.__cbotMore.length) {
      botSay(() => { botBubble(`בכיף, עוד כמה:`); window.__cbotMore.slice(0, 3).forEach(productCard); window.__cbotMore = window.__cbotMore.slice(3); chips(window.__cbotMore.length ? ["עוד אפשרויות ➕", "דבר עם נציג 💬"] : ["דבר עם נציג 💬"]); });
      return;
    }
    if (/^כל המוצרים/.test(t)) { botSay(() => { botBubble(`הנה כמה מהמובילים — לצפייה בכל הקטלוג <a href="products.html" style="color:var(--blue);font-weight:700">לחצו כאן</a>:`); products().slice(0, 3).forEach(productCard); }); return; }
    if (/^המלצה לפי תקציב/.test(t) || /תקציב\??$/.test(t)) { awaiting = "budget"; botSay(() => botBubble(`בכיף 💰 מה התקציב שלכם בשקלים? (למשל: 1500)`)); return; }

    if (it.faq) { faqReply(it.faq); return; }
    if (it.greet) { botSay(() => { botBubble(`היי! 😊 מה אתם מחפשים היום?`); chips(["מחשב לעסק 💼", "יד שנייה ♻️", "המלצה לפי תקציב 💰"]); }); return; }
    if (it.thanks) { botSay(() => botBubble(`שמחתי לעזור! 🙌 יש עוד משהו שאפשר לעזור בו?`)); return; }

    // any product-ish intent → recommend
    if (it.budget || it.type || it.use || it.cond || it.brand || it.specs) {
      const bits = [];
      if (it.cond === "used") bits.push("יד שנייה");
      if (it.use === "business") bits.push("לעסק");
      if (it.use === "gaming") bits.push("לגיימינג");
      if (it.type === "monitor") bits.push("מסך");
      if (it.brand) bits.push(it.brand);
      if (it.budget) bits.push("עד " + ils(it.budget));
      resultsFor(it, bits.length ? `חיפשתם ${bits.join(" · ")} — הנה ההמלצות שלי:` : null);
      return;
    }

    // fallback
    botSay(() => {
      botBubble(`לא בטוח שהבנתי במדויק 🤔 אפשר לנסות אחת מאלה, או לכתוב תקציב וסוג מוצר:`);
      chips(["מחשב לעסק 💼", "יד שנייה ♻️", "המלצה לפי תקציב 💰", "משלוח ואחריות 🚚", "דבר עם נציג 💬"]);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
})();
