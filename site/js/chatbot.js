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

  /* ---------- normalization ---------- */
  // collapse stretched letters (חייייבב → חיב), strip niqqud + punctuation, lowercase
  function normalize(t) {
    let s = String(t || "").toLowerCase();
    s = s.replace(/[֑-ׇ]/g, "");           // niqqud/te'amim
    s = s.replace(/["'׳״`.!?,:;()\[\]{}\-–—]/g, " "); // punctuation
    s = s.replace(/([֐-׿a-z])\1{1,}/g, "$1"); // collapse repeats: אאא→א, לוווו→לו
    s = s.replace(/\s+/g, " ").trim();
    return " " + s + " ";
  }

  /* ---------- intent parsing ---------- */
  function parse(t) {
    const s = normalize(t);
    const it = { raw: t };

    // budget — many forms: "עד 1500", "בסביבות 2000", "1500 שח", "1500ש", "1.5k", or just a bare number
    const rawNum = t.replace(/,/g, "");
    let bud =
      rawNum.match(/(?:עד|תקציב|מקסימום|מקס|בסביבות|במסגרת|לא יותר מ|לא יותר|בערך|כ ?)\D{0,4}(\d{3,6})/) ||
      rawNum.match(/(\d{3,6})\s*(?:₪|שקל|שח|ש["׳]|ש)/) ||
      rawNum.match(/(\d(?:\.\d)?)\s*(?:k|קי|K)\b/i) ||
      rawNum.match(/^\s*(\d{3,6})\s*$/);
    if (bud) {
      let n = parseFloat(bud[1]);
      if (/k|קי|K/i.test(bud[0]) && n < 20) n = Math.round(n * 1000);
      it.budget = Math.round(n);
    }

    // cheap / expensive / best (works without any budget number)
    if (/זול|הכי זול|הכי משתלם|הזול|משתלם|בזול|במחיר טוב|במחיר נמוך|לא יקר|בזול/.test(s)) it.pricePref = "low";
    else if (/יקר|פרימיום|הכי טוב|הטוב ביותר|טופ|top|הכי חזק|החזק|premium/.test(s)) it.pricePref = "high";

    // urgency / availability
    if (/דחוף|מיד|עכשיו|מהר|בזריז|בזרז|בזירז|היום|במלאי|יש במלאי|לקנות עכשיו|חייב עכשיו|אני חיב/.test(s)) it.urgent = true;

    // upgrade / need something
    if (/צריך|צריכה|רוצה|מחפש|מחפשת|מעונין|מעונינת|יש לכם|יש לך|מה יש|מה אתם ממליצים|תמליץ|תמליצי|המלץ|המליצו|חיב|חיבת/.test(s)) it.want = true;

    // use-case
    if (/עסק|משרד|עבוד|חברה|ארגון|אקסל|וורד|זום|אאוטלוק/.test(s)) it.use = "business";
    else if (/גיימינג|גיימ|משחק|gaming|פורטנייט|fortnite|cs|קאונטר|לול|lol|fifa/.test(s)) it.use = "gaming";
    else if (/סטודנט|לימוד|בית ספר|אוניברסיט|קמפוס/.test(s)) it.use = "student";
    else if (/בית|ביתי|גלישה|נטפליקס|יוטיוב|יומיום|לילדים|לילד|לילדה|לאמא|לאבא|לסבתא|לסבא/.test(s)) it.use = "home";
    else if (/עריכ|וידאו|גרפי|render|רנדר|כבד|תובעני|פוטושופ|פרימייר|premiere|פיתוח|dev|coding|קוד|תלת מימד|3d/.test(s)) it.use = "heavy";

    // product type — includes many colloquial variants
    if (/נייד|לפטופ|laptop|מחברת|מקבוק|macbook|מאקבוק/.test(s)) it.type = "laptop";
    else if (/נייח|דסקטופ|מגדל|desktop|tiny|מיני|מיקרו|micro|טאואר|tower/.test(s)) it.type = "desktop";
    else if (/\bמסך\b|מוניטור|monitor|צג|תצוגה/.test(s)) it.type = "monitor";
    else if (/מקלדת|עכבר|כבל|מטען|אופיס|office|אביזר|אזניות|אוזני|רמקול|מיקרופון|מדפסת|סורק/.test(s)) it.type = "accessory";
    else if (/באנדל|חביל|חבילה|מארז|bundle|קומפלט|קומפלה/.test(s)) it.type = "bundle";
    else if (/\bמחשב\b|מחשוב|pc/.test(s)) it.type = "computer"; // generic — laptop OR desktop

    // condition
    if (/יד ?שני|מחודש|משומש|רפרביש|refurb|יד2|יד ב/.test(s)) it.cond = "used";
    else if (/חדש לגמרי|חדשים|חדש|new|באריזה|מוגדר/.test(s)) it.cond = "new";

    // brand
    if (/לנובו|lenovo|thinkpad|thinkcentre|קפדן/.test(s)) it.brand = "Lenovo";
    else if (/\bhp\b|elitedesk|probook|היו?לט|אצ ?פי/.test(s)) it.brand = "HP";
    else if (/\bdell\b|דל|latitude|optiplex|לטיטיוד|אופטיפלקס/.test(s)) it.brand = "Dell";
    else if (/apple|אפל|mac|מק|macbook|imac/.test(s)) it.brand = "Apple";
    else if (/asus|אסוס/.test(s)) it.brand = "ASUS";

    // specs
    const specs = [];
    if (/32 ?gb|32 ?ג/.test(s)) specs.push("32GB");
    else if (/16 ?gb|16 ?ג/.test(s)) specs.push("16GB");
    else if (/8 ?gb|8 ?ג/.test(s)) specs.push("8GB");
    if (/i7|איי? ?7|קור ?7|core ?7/.test(s)) specs.push("i7");
    else if (/i5|איי? ?5|קור ?5|core ?5/.test(s)) specs.push("i5");
    if (/512/.test(s)) specs.push("512GB");
    else if (/256/.test(s)) specs.push("256GB");
    if (/1 ?tb|1 ?טרה|טרה/.test(s)) specs.push("1TB");
    if (specs.length) it.specs = specs;

    // FAQ intents
    if (/משלוח|מתי מגיע|זמן אספק|שילוח|איך שולחים|לוקח זמן/.test(s)) it.faq = "shipping";
    else if (/אחריות|warranty|תיקון|קלקל|מתקלק|נשבר|שבור|יש בעיה|תקוע/.test(s)) it.faq = "warranty";
    else if (/תשלום|אשראי|קרדיט|פייבוקס|ביט|תשלומים|payment|לשלם|במזומן/.test(s)) it.faq = "payment";
    else if (/החזר|ביטול|לא מרוצה|return|refund|להחזיר/.test(s)) it.faq = "returns";
    else if (/מה זה יד|למה יד שני|מחודש זה|refurb\?|מה זה מחודש|יד שני?ה זה/.test(s)) it.faq = "refurb";
    else if (/נציג|אנוש|טלפון|וואטסאפ|whatsapp|לדבר עם|צור קשר|מוקד|שרות|שירות/.test(s)) it.faq = "contact";

    // greetings / thanks
    if (/^(שלום|הי|הלו|אהלן|אהלה|בוקר טוב|ערב טוב|יו|hello|hey|hi|sup)\b/.test(s.trim())) it.greet = true;
    if (/תודה|thanks|יופי|מעולה|סבבה|וואלה|אחלה/.test(s)) it.thanks = true;

    return it;
  }

  function recommend(it) {
    let list = products().slice().filter((p) => p.price > 0);
    // If no explicit type: exclude accessories (nobody comes here to buy a 25₪ cable when asking for "משהו זול").
    // Accessories only appear when the user explicitly asked for one.
    if (!it.type) list = list.filter((p) => ptype(p) !== "accessory");
    else if (it.type !== "computer") list = list.filter((p) => ptype(p) === it.type);
    if (it.type === "computer") list = list.filter((p) => ptype(p) === "laptop" || ptype(p) === "desktop");
    if (it.cond === "used") list = list.filter((p) => p.category === "יד שנייה");
    if (it.cond === "new") list = list.filter((p) => p.category === "מחשבים חדשים");
    if (it.brand) list = list.filter((p) => p.brand === it.brand);
    if (it.budget) list = list.filter((p) => p.price <= it.budget);
    if (it.specs) list = list.filter((p) => it.specs.every((sp) => (p.specs || "").toUpperCase().includes(sp.toUpperCase())));
    if (it.use === "business" || it.use === "student" || it.use === "home")
      list = list.filter((p) => ptype(p) === "laptop" || ptype(p) === "desktop");
    if (it.use === "heavy") list = list.filter((p) => /i7|32GB|16GB/i.test(p.specs || ""));
    if (it.urgent) list = list.filter((p) => p.status === "stock" || !p.status);
    // sort: pricePref wins, else default cheap→expensive
    if (it.pricePref === "high") list.sort((a, b) => b.price - a.price);
    else list.sort((a, b) => a.price - b.price);
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
    const hasIntent = it.budget || it.type || it.use || it.cond || it.brand || it.specs || it.pricePref || it.urgent || it.want;
    if (hasIntent) {
      const bits = [];
      if (it.pricePref === "low") bits.push("הכי משתלם");
      if (it.pricePref === "high") bits.push("הפרימיום שלנו");
      if (it.urgent) bits.push("מוכן במלאי");
      if (it.cond === "used") bits.push("יד שנייה");
      if (it.cond === "new") bits.push("חדש");
      if (it.use === "business") bits.push("לעסק");
      if (it.use === "gaming") bits.push("לגיימינג");
      if (it.use === "student") bits.push("לסטודנטים");
      if (it.use === "home") bits.push("לבית");
      if (it.use === "heavy") bits.push("לעבודה כבדה");
      if (it.type === "laptop") bits.push("מחשב נייד");
      else if (it.type === "desktop") bits.push("מחשב נייח");
      else if (it.type === "monitor") bits.push("מסך");
      else if (it.type === "accessory") bits.push("אביזרים");
      else if (it.type === "bundle") bits.push("באנדל");
      else if (it.type === "computer") bits.push("מחשב");
      if (it.brand) bits.push(it.brand);
      if (it.budget) bits.push("עד " + ils(it.budget));
      const intro = bits.length
        ? `הבנתי — ${bits.join(" · ")}. הנה מה שיש לי בשבילכם:`
        : `בכיף, הנה כמה המלצות מעולות מהמלאי:`;
      resultsFor(it, intro);
      return;
    }

    // fallback — try to still help
    botSay(() => {
      botBubble(`לא הצלחתי לפענח בדיוק את הבקשה 🤔 אבל בואו ננסה אחרת — מה מתאים לכם?`);
      chips(["הכי זול שיש 💸", "מחשב לעסק 💼", "מחשב נייד 💻", "מחשב נייח 🖥️", "יד שנייה ♻️", "המלצה לפי תקציב 💰", "דבר עם נציג 💬"]);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
})();
