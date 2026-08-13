/* ============================================================
   BIG BRANDS — עוזר קנייה חכם (client-side, ללא שרת)
   ------------------------------------------------------------
   מנוע NLU עברי/אנגלי:
     1. נרמול   — ניקוד, אותיות סופיות, סלנג מתוח, פיסוק
     2. פאזי    — Levenshtein לשגיאות כתיב
     3. ניקוד   — כל קטגוריה מקבלת ציון, הגבוה מנצח (לא if/else)
     4. הרפיה   — אם אין תוצאות, מרפים מסננים בהדרגה במקום "לא מצאתי"
     5. ידע     — בסיס ידע מלא של החנות (משלוח, אחריות, החזרות, מיקום…)
     6. זיכרון  — הקשר נשמר בין הודעות (תקציב, סוג, מותג)
   ============================================================ */
(function () {
  "use strict";

  /* ══════════════════════════════════════════════════════════
     בסיס ידע — עובדות החנות
     ══════════════════════════════════════════════════════════ */
  const BIZ = {
    name: "ביג ברנדס",
    phone: "0508808076",
    phoneNice: "050-880-8076",
    email: "bigbrands10@gmail.com",
    wa: "972508808076",
    address: "רוטשילד 55, ראשון לציון",
  };

  const ils = (n) => Number(n).toLocaleString("he-IL") + " ₪";
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const products = () => (window.Store ? Store.getProducts() : (window.SITE_DATA ? SITE_DATA.products : []));
  const waLink = (msg) => `https://wa.me/${BIZ.wa}?text=${encodeURIComponent(msg)}`;
  const link = (href, txt) => `<a href="${href}" style="color:var(--blue);font-weight:700">${txt}</a>`;

  /* ══════════════════════════════════════════════════════════
     1. נרמול טקסט
     ══════════════════════════════════════════════════════════ */
  const FINALS = { "ם": "מ", "ן": "נ", "ץ": "צ", "ף": "פ", "ך": "כ" };
  const definalize = (s) => s.replace(/[םןץףך]/g, (c) => FINALS[c]);

  /* בונה RegExp שסובל אותיות סופיות — אפשר לכתוב תבניות בעברית טבעית */
  const rx = (src, flags) => new RegExp(definalize(src), flags);

  function normalize(raw) {
    let s = String(raw || "").toLowerCase();
    s = s.replace(/[֑-ׇ]/g, "");                 // ניקוד וטעמים
    s = definalize(s);                                      // ם ן ץ ף ך → מ נ צ פ כ
    s = s.replace(/[^א-תa-z0-9\s]/g, " ");        // פיסוק, אימוג'י, גרשיים
    s = s.replace(/\s+/g, " ").trim();
    // "squeezed": מכווץ אותיות חוזרות — חייייבבב → חיב, אחלהההה → אחלה
    const sq = s.replace(/(.)\1+/g, "$1");
    return { s: " " + s + " ", sq: " " + sq + " ", tokens: s.split(" ").filter(Boolean) };
  }

  /* ══════════════════════════════════════════════════════════
     2. התאמה פאזית — תופס שגיאות כתיב
     ══════════════════════════════════════════════════════════ */
  /* Damerau-Levenshtein — סופר החלפת אותיות סמוכות כטעות אחת.
     חשוב: "לנווב"→"לנובו" זו טעות אחת, בעוד "לשלם"→"משתלם" נשאר 2 (ולכן נדחה). */
  function dlev(a, b) {
    if (a === b) return 0;
    const m = a.length, n = b.length;
    if (!m || !n) return Math.max(m, n);
    const d = [];
    for (let i = 0; i <= m; i++) { d[i] = new Array(n + 1).fill(0); d[i][0] = i; }
    for (let j = 0; j <= n; j++) d[0][j] = j;
    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        const cost = a[i - 1] === b[j - 1] ? 0 : 1;
        d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost);
        if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
          d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);   // שיכול אותיות
        }
      }
    }
    return d[m][n];
  }

  /* מילים שמותר לזהות עם שגיאת כתיב (רק מילות מפתח ארוכות — למנוע התאמות שווא) */
  const FUZZY_WORDS = {
    computer: ["מחשב", "computer"],
    laptop:   ["נייד", "לפטופ", "laptop", "מקבוק", "macbook", "טינקפאד", "טינקפד", "thinkpad"],
    desktop:  ["דסקטופ", "desktop", "מיקרו", "טינקסנטר", "תינקסנטר", "thinkcentre"],
    monitor:  ["מסך", "מוניטור", "monitor"],
    low:      ["זול", "משתלם", "חסכוני", "cheap"],
    Lenovo:   ["לנובו", "lenovo", "thinkpad", "טינקפד", "טינקפאד", "טינקסנטר", "תינקסנטר"],
    HP:       ["elitedesk", "probook", "elitebook"],
    Dell:     ["latitude", "optiplex", "לטיטיוד"],
    Apple:    ["macbook", "מקבוק", "אפל"],
    ASUS:     ["asus", "אסוס"],
    shipping: ["משלוח", "שילוח", "אספקה"],
    warranty: ["אחריות", "warranty"],
  };

  function fuzzyHit(ctx, key) {
    const words = FUZZY_WORDS[key] || [];
    return words.some((w) => {
      if (w.length < 5) return false;   // מילים קצרות מדי → "נגיד" היה נתפס כ"נייד"
      const maxD = w.length >= 8 ? 2 : 1;   // מרווח צר — Damerau כבר סופר שיכול כטעות אחת
      const target = definalize(w.toLowerCase());
      return ctx.tokens.some((t) => Math.abs(t.length - target.length) <= maxD && dlev(t, target) <= maxD);
    });
  }

  /* ══════════════════════════════════════════════════════════
     3. לקסיקון — עברית, אנגלית, סלנג, תעתיקים
     ══════════════════════════════════════════════════════════ */
  const L = {
    use: {
      business: [
        "עסק", "עסקי", "עסקים", "משרד", "משרדי", "עבודה", "לעבוד", "חברה", "ארגון", "צוות", "עובדים",
        "אקסל", "excel", "וורד", "word", "זום", "zoom", "אאוטלוק", "outlook", "טימס", "teams",
        "business", "work", "office", "מנהל", "מנהלת", "רואה חשבון", "עורך דין", "קליניקה", "מרפאה",
        "סטארטאפ", "startup", "משרדית", "עמדת עבודה", "לפירמה", "לחברה", "מחשב לעבודה",
      ],
      gaming: [
        "גיימינג", "גיימר", "גיימרים", "משחק", "משחקים", "לשחק", "gaming", "gamer", "games",
        "פורטנייט", "fortnite", "מיינקראפט", "minecraft", "רובלוקס", "roblox", "ולורנט", "valorant",
        "קאונטר", "counter", "csgo", "cs2", "פיפא", "fifa", "gta", "לול", "league", "apex", "fps",
      ],
      student: [
        "סטודנט", "סטודנטית", "סטודנטים", "לימוד", "לימודים", "ללמוד", "אוניברסיטה", "מכללה",
        "בית ספר", "תיכון", "קמפוס", "תואר", "student", "school", "college", "university",
        "שיעורי בית", "עבודות", "מבחנים",
      ],
      home: [
        "בית", "ביתי", "לבית", "גלישה", "לגלוש", "אינטרנט", "נטפליקס", "netflix", "יוטיוב", "youtube",
        "סרטים", "סדרות", "יומיום", "יומיומי", "לילדים", "לילד", "לילדה", "לאמא", "לאבא",
        "לסבתא", "לסבא", "להורים", "בסיסי", "לא מסובך", "רק לגלישה",
      ],
      heavy: [
        "עריכה", "עריכת", "וידאו", "video", "גרפיקה", "גרפי", "עיצוב", "render", "רנדר",
        "פוטושופ", "photoshop", "פרימייר", "premiere", "אילוסטרייטור", "illustrator",
        "אפטר", "after effects", "תלת מימד", "3d", "cad", "autocad", "אוטוקאד", "סולידוורקס",
        "בלנדר", "blender", "תכנות", "פיתוח", "לתכנת", "קוד", "coding", "programming", "developer",
        "מתכנת", "מפתח", "docker", "דוקר", "וירטואלי", "מכונות וירטואליות", "כבד", "תובעני",
        "מקצועי", "סטרימינג", "streaming", "מונטאז", "מונטז", "אנימציה",
      ],
    },
    type: {
      laptop: [
        "נייד", "ניידים", "ניידת", "לפטופ", "laptop", "notebook", "מחברת", "מקבוק", "macbook",
        "thinkpad", "latitude", "probook", "elitebook", "לקחת איתי", "ניידות", "לטיסות",
        "לנסיעות", "בתיק", "על הברכיים", "לקחת לכל מקום",
      ],
      desktop: [
        "נייח", "נייחים", "desktop", "מגדל", "tower", "טאואר", "מיני", "mini", "מיקרו", "micro",
        "sff", "tiny", "שולחני", "על השולחן", "thinkcentre", "elitedesk", "optiplex", "prodesk",
        "טינקסנטר", "תינקסנטר", "אליטדסק", "קבוע במשרד", "מחשב שולחן", "עמדה קבועה",
      ],
      monitor: ["מסך", "מסכים", "מוניטור", "monitor", "צג", "צגים", "display", "מסך מחשב"],
      bundle: [
        "באנדל", "bundle", "חבילה", "חבילות", "מארז", "קומפלט", "ערכה", "סט", "combo",
        "הכל ביחד", "כולל הכל", "עמדה מלאה", "עמדת עבודה מלאה", "הכל כלול",
      ],
      computer: ["מחשב", "מחשבים", "מחשוב", "computer", "pc", "machine", "מכונה"],
      /* אחרון בכוונה — בתיקו, "מחשב" מנצח "אביזר" */
      accessory: [
        "מקלדת", "keyboard", "עכבר", "mouse", "כבל", "כבלים", "cable", "hdmi", "מטען", "charger",
        "אוזניות", "אזניות", "headphones", "רמקול", "speaker", "מיקרופון", "דוק", "dock",
        "מתאם", "adapter", "אביזר", "אביזרים", "נרתיק", "אופיס", "office 365", "microsoft office", "רישיון",
      ],
    },
    cond: {
      used: [
        "יד שניה", "יד שנייה", "יד2", "יד ב", "מחודש", "מחודשים", "מחודשת", "משומש", "משומשים",
        "רפרביש", "refurb", "refurbished", "used", "second hand", "secondhand", "משופץ", "שופץ",
      ],
      new: ["חדש", "חדשה", "חדשים", "new", "brand new", "באריזה", "סגור באריזה", "מהיצרן", "מפעל"],
    },
    brand: {
      Lenovo: ["lenovo", "לנובו", "לינובו", "thinkpad", "thinkcentre", "טינקפד", "טינקפאד",
        "טינקסנטר", "תינקסנטר", "ideapad", "לנבו"],
      HP:     ["hp", "אייצפי", "hewlett", "packard", "elitedesk", "probook", "elitebook", "prodesk", "אליטדסק", "פרובוק"],
      Dell:   ["dell", "דל", "latitude", "optiplex", "לטיטיוד", "אופטיפלקס", "inspiron", "xps", "לטיטיוד"],
      Apple:  ["apple", "אפל", "mac", "macbook", "מקבוק", "מק בוק", "imac", "מקינטוש", "macos"],
      ASUS:   ["asus", "אסוס", "zenbook", "vivobook", "rog", "expertbook"],
      MAG:    ["mag", "מאג"],
      Logitech: ["logitech", "לוגיטק"],
      Microsoft: ["microsoft", "מיקרוסופט"],
    },
    pricePref: {
      low: [
        "זול", "זולה", "זולים", "בזול", "הכי זול", "משתלם", "משתלמת", "כלכלי", "חסכוני", "לא יקר",
        "cheap", "cheapest", "budget", "affordable", "מציאה", "דיל", "deal", "עסקה טובה",
        "בכמה שפחות", "מעט כסף", "אין לי הרבה", "מוגבל בתקציב", "בתקציב נמוך", "גרושים", "בזיל",
        "כמה שיותר זול", "פחות כסף", "לא רוצה לבזבז", "הכי משתלם",
      ],
      high: [
        "יקר", "פרימיום", "premium", "הכי טוב", "הטוב ביותר", "טופ", "top", "best", "high end",
        "הכי חזק", "החזק ביותר", "חזק", "מפלצת", "beast", "בלי הגבלה", "לא משנה המחיר",
        "הכי מהיר", "הכי חדש", "flagship", "מפרט גבוה",
      ],
    },
    urgent: [
      "דחוף", "מיד", "עכשיו", "מהר", "בזריז", "בזרז", "היום", "מחר", "כמה שיותר מהר",
      "אין לי זמן", "צריך עכשיו", "urgent", "asap", "מהיום", "בדחיפות", "מתי אפשר לקבל",
    ],
    want: [
      "צריך", "צריכה", "רוצה", "מחפש", "מחפשת", "מעוניין", "מעונינת", "יש לכם", "יש לך",
      "מה יש", "תמליץ", "תמליצי", "המלץ", "המליצו", "ממליץ", "חייב", "חייבת", "אשמח",
      "want", "need", "looking for", "recommend", "show me", "תראה לי", "תציע", "אפשר לראות",
    ],
  };

  /* נושאי ידע — כל נושא עם מילות מפתח */
  const TOPICS = {
    shipping: ["משלוח", "משלוחים", "שילוח", "אספקה", "מתי מגיע", "כמה זמן לוקח", "זמן אספקה",
      "שליח", "עד הבית", "delivery", "shipping", "ship", "לאיזה אזורים", "משלוח חינם", "דואר",
      "איסוף עצמי", "לאסוף", "לשלוח"],
    warranty: ["אחריות", "warranty", "תיקון", "מתקלקל", "התקלקל", "נשבר", "שבור", "לא עובד",
      "יש בעיה", "תקוע", "מעבדה", "שירות", "אחראים", "כמה זמן אחריות", "מה קורה אם"],
    returns: ["החזר", "החזרה", "להחזיר", "ביטול", "לבטל", "לא מרוצה", "return", "refund",
      "כסף בחזרה", "14 יום", "אם לא אהבתי", "דמי ביטול"],
    payment: ["תשלום", "תשלומים", "לשלם", "אשראי", "כרטיס", "קרדיט", "ביט", "bit", "פייבוקס",
      "paybox", "מזומן", "העברה בנקאית", "payment", "credit", "בכמה תשלומים", "חשבונית", "קבלה", "מעמ"],
    refurb: ["מה זה מחודש", "מה זה יד שניה", "למה יד שניה", "refurbished מה", "איך אתם בודקים",
      "זה אמין", "זה טוב", "כמה זה משומש", "מצב המחשב", "שריטות", "איך המצב"],
    location: ["איפה אתם", "כתובת", "מיקום", "חנות", "סניף", "להגיע", "לבוא", "where are you",
      "address", "location", "ראשון לציון", "רוטשילד", "יש חנות", "אפשר לראות פיזית"],
    contact: ["נציג", "אנושי", "טלפון", "להתקשר", "וואטסאפ", "ואטסאפ", "whatsapp", "לדבר עם",
      "צור קשר", "ליצור קשר", "מוקד", "מייל", "אימייל", "email", "לדבר עם בן אדם"],
    hours: ["שעות", "מתי פתוח", "פתוחים", "סגורים", "שעות פעילות", "hours", "open", "שבת", "יום שישי"],
    vat: ["מעמ", "כולל מעמ", "מחיר סופי", "יש הפתעות", "עוד עלויות", "מחיר כולל"],
    os: ["מערכת הפעלה", "windows", "ווינדוס", "חלונות", "win11", "win10", "לינוקס", "linux",
      "מותקן", "רישיון", "אופיס", "office 365", "microsoft office", "מקורי"],
    upgrade: ["שדרוג", "לשדרג", "להוסיף זיכרון", "להוסיף ram", "דיסק גדול יותר", "ssd נוסף",
      "upgrade", "אפשר להרחיב", "חריץ פנוי"],
    business: ["הצעת מחיר", "כמות", "הרבה מחשבים", "לחברה", "עוסק מורשה", "חשבונית מס",
      "מכרז", "bulk", "quote", "לארגון", "10 מחשבים", "כמה יחידות"],
    catalog: ["מה יש לכם", "מה אתם מוכרים", "מה המוצרים", "קטלוג", "רשימה", "כל המוצרים",
      "what do you sell", "catalog", "מה הקטגוריות", "מה יש במלאי"],
  };

  /* שיחת חולין */
  const SMALLTALK = {
    greet: ["שלום", "היי", "הי", "הלו", "אהלן", "אהלה", "יו", "בוקר טוב", "צהריים טובים",
      "ערב טוב", "לילה טוב", "hello", "hey", "hi", "yo", "sup", "מה קורה", "מה נשמע", "מה המצב"],
    thanks: ["תודה", "תודה רבה", "thanks", "thank you", "ty", "יופי", "מעולה", "סבבה", "אחלה",
      "מדהים", "פצצה", "אלוף", "אלופה", "מושלם", "נהדר"],
    bye: ["ביי", "להתראות", "יאללה ביי", "bye", "goodbye", "צאט", "נדבר", "תודה ביי", "סיימתי"],
    bot: ["אתה בוט", "את בוט", "מי אתה", "מי את", "אתה רובוט", "אתה אדם", "ai", "בינה מלאכותית",
      "are you a bot", "who are you", "אתה אמיתי"],
    howareyou: ["מה שלומך", "איך אתה", "how are you", "מה איתך"],
    joke: ["בדיחה", "תצחיק", "משעמם", "joke", "haha", "חחח", "לול", "lol"],
    help: ["עזרה", "תעזור", "איך זה עובד", "מה אתה יודע", "מה אתה יכול", "help", "אני אבוד",
      "לא יודע מה לבחור", "תעזור לי לבחור", "מבולבל"],
  };

  /* ══════════════════════════════════════════════════════════
     4. סיווג מוצרים
     ══════════════════════════════════════════════════════════ */
  function ptype(p) {
    if (p.category === "מסכים") return "monitor";
    if (p.category === "אביזרים") return "accessory";
    if (p.category === "באנדלים") return "bundle";
    if (/ThinkCentre|EliteDesk|ProDesk|OptiPlex|נייח|\bMini\b|\bMicro\b|\bSFF\b|\bDM\b|M900|M93p/i.test(p.name)) return "desktop";
    return "laptop";
  }
  const TYPE_HE = { laptop: "מחשב נייד", desktop: "מחשב נייח", monitor: "מסך", accessory: "אביזר", bundle: "באנדל", computer: "מחשב" };

  /* ══════════════════════════════════════════════════════════
     5. ניתוח כוונה — מבוסס ניקוד
     ══════════════════════════════════════════════════════════ */
  /* מורפולוגיה עברית: תחיליות (ל/ב/ה/ו/מ/ש/כ) וסופיות נטייה.
     בלעדיהן "לעסק" לא היה מזוהה כ-"עסק" ו-"לסטודנטית" לא כ-"סטודנט". */
  const PRE = "[ולבהמשכ]{0,2}";
  const SUF = "(ים|ות|יות|ית|יה|ה|ת|י|ו|ן|ם)?";
  const reCache = new Map();
  function wordRe(w) {
    let re = reCache.get(w);
    if (!re) {
      const pat = definalize(w.toLowerCase()).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      re = new RegExp("(^| )" + definalize(PRE) + pat + definalize(SUF) + "( |$)");
      reCache.set(w, re);
    }
    return re;
  }
  function hits(ctx, words) {
    let n = 0;
    for (const w of words) {
      const re = wordRe(w);
      if (re.test(ctx.s) || re.test(ctx.sq)) n++;
    }
    return n;
  }
  /* בוחר את הקטגוריה עם הכי הרבה פגיעות */
  function best(ctx, dict, fuzzyKeys) {
    let winner = null, top = 0;
    for (const k in dict) {
      let n = hits(ctx, dict[k]);
      if (fuzzyKeys && !n && fuzzyHit(ctx, k)) n = 0.5;
      if (n > top) { top = n; winner = k; }
    }
    return top > 0 ? winner : null;
  }
  /* שני הנושאים המובילים — לשאלות שמשלבות שני דברים */
  function bestTwo(ctx, dict) {
    const scored = Object.keys(dict).map((k) => ({ k, n: hits(ctx, dict[k]) })).filter((x) => x.n > 0);
    scored.sort((a, b) => b.n - a.n);
    return scored.slice(0, 2).map((x) => x.k);
  }

  function parse(raw) {
    const ctx = normalize(raw);
    const it = { raw, ctx };

    /* — תקציב — */
    const clean = raw.replace(/,/g, "");
    const m =
      clean.match(/(?:עד|תקציב|מקסימו?ם|מקס|בסביבות|סביב|במסגרת|לא יותר מ|בערך|כמו|around|under|max)\D{0,6}(\d{3,6})/i) ||
      clean.match(/(\d{3,6})\s*(?:₪|ש["']?ח|שקל|שקלים|nis|ils)/i) ||
      clean.match(/(\d(?:[.,]\d)?)\s*(?:k|קי)\b/i) ||
      clean.match(/^\s*(\d{3,6})\s*$/);
    if (m) {
      let n = parseFloat(String(m[1]).replace(",", "."));
      if (/k|קי/i.test(m[0]) && n < 30) n = Math.round(n * 1000);
      if (n >= 100) it.budget = Math.round(n);
    }
    /* מספרים במילים: "עד אלף שקל", "אלפיים וחצי" */
    if (!it.budget) {
      const NUMWORDS = [["חמשת אלפים", 5000], ["ארבעת אלפים", 4000], ["שלושת אלפים", 3000],
        ["אלפיים וחצי", 2500], ["אלף וחצי", 1500], ["אלפיים", 2000], ["אלף", 1000]];
      for (const [w, v] of NUMWORDS) {
        if (rx("(^| )[ולבהמשכ]{0,2}" + w + "( |$)").test(ctx.s)) { it.budget = v; break; }
      }
    }
    if (/בערך|בסביבות|סביב|כמו|בגדול|משהו כמו|around|about/i.test(raw)) it.approx = true;

    /* — קטגוריות מנוקדות — */
    it.use = best(ctx, L.use);
    it.cond = best(ctx, L.cond);
    it.brand = best(ctx, L.brand, true);
    it.pricePref = best(ctx, L.pricePref, true);

    /* סוג מוצר — "מחשב" גנרי רק אם לא נאמר נייד/נייח */
    const typeScores = {};
    for (const k in L.type) typeScores[k] = hits(ctx, L.type[k]);
    ["laptop", "desktop", "monitor", "computer"].forEach((k) => { if (!typeScores[k] && fuzzyHit(ctx, k)) typeScores[k] = 0.5; });
    // שאלת השוואה: "נייד או נייח מה עדיף" — שניהם הוזכרו יחד עם מילת השוואה
    if (typeScores.laptop && typeScores.desktop && rx("מה עדיף|מה יותר טוב|מה ההבדל|או נייח|או נייד|vs|לעומת|מה כדאי").test(ctx.s)) {
      it.compare = "laptop-vs-desktop";
    }
    // "מחשב" גנרי מפנה מקום ל"נייד"/"נייח" אם נאמרו במפורש
    if (typeScores.laptop || typeScores.desktop) typeScores.computer = 0;
    let tTop = 0;
    for (const k in typeScores) if (typeScores[k] > tTop) { tTop = typeScores[k]; it.type = k; }
    if (!tTop) it.type = null;

    it.urgent = hits(ctx, L.urgent) > 0;
    it.want = hits(ctx, L.want) > 0;

    /* — מפרט — */
    const specs = [];
    if (/32 ?gb|32 ?ג/i.test(ctx.s)) specs.push("32GB");
    else if (/16 ?gb|16 ?ג/i.test(ctx.s)) specs.push("16GB");
    else if (/8 ?gb|8 ?ג/i.test(ctx.s)) specs.push("8GB");
    if (/i7|אי+ ?7|קור ?7|core ?7/i.test(ctx.s)) specs.push("i7");
    else if (/i5|אי+ ?5|קור ?5|core ?5/i.test(ctx.s)) specs.push("i5");
    if (/1 ?tb|1 ?טרה|טרהבייט/i.test(ctx.s)) specs.push("1TB");
    else if (/512/.test(ctx.s)) specs.push("512GB");
    else if (/256/.test(ctx.s)) specs.push("256GB");
    if (specs.length) it.specs = specs;

    /* מספר "עירום" במשפט = תקציב ("בוא נגיד 2500 מה יש").
       נזהרים לא לבלוע מספרי מפרט (512 SSD) או כמויות (10 מחשבים). */
    if (!it.budget) {
      const bare = clean.match(/(?:^|\s)(\d{3,6})(?!\s*(?:gb|tb|ג["׳]?ב|גיגה|טרה|ssd|nvme|mhz|ghz|hz|w|וואט))/i);
      if (bare) {
        const n = parseInt(bare[1]);
        const isSpecNum = specs.some((sp) => sp.indexOf(String(n)) === 0);
        if (n >= 300 && n <= 99999 && !isSpecNum) it.budget = n;
      }
    }

    /* — נושא ידע (עד שניים, לשאלות משולבות) — */
    const tops = bestTwo(ctx, TOPICS);
    it.topic = tops[0] || null;
    it.topic2 = tops[1] || null;
    /* — שיחת חולין — */
    it.small = best(ctx, SMALLTALK);

    /* — סופרלטיבים — */
    if (rx("הכי זול|זול ביותר|cheapest").test(ctx.s)) { it.pricePref = "low"; it.superlative = "low"; }
    if (rx("הכי חזק|הכי טוב|הכי מהיר|best|strongest").test(ctx.s)) { it.pricePref = "high"; it.superlative = "high"; }

    return it;
  }

  /* ══════════════════════════════════════════════════════════
     6. המלצה — סינון עם הרפיה הדרגתית + דירוג
     ══════════════════════════════════════════════════════════ */
  /* מפרט חזק באמת — "עד 32GB" זו תמיכה מקסימלית, לא מה שמותקן */
  function isPerf(p) {
    const spec = (p.specs || "").replace(/עד\s*\d+\s*GB/gi, "");
    return /i7|M5|32GB/i.test(spec + " " + p.name);
  }

  /* התאמת שם מוצר — "מקלדת ועכבר" צריך להחזיר את המקלדת, לא כבל זול */
  const STOP = new Set([
    "אני", "יש", "לי", "לך", "לכם", "את", "של", "עם", "זה", "מה", "על", "אבל",
    "רוצה", "צריכ", "מחפש", "משהו", "בבקשה", "תודה", "כמה", "איזה", "הכי", "עוד", "גם", "אם",
    "the", "for", "you", "have", "need", "want", "with", "and", "what", "your", "any", "can", "show", "give",
    /* מילות קטגוריה גנריות — הסינון כבר טיפל בהן, אסור שיטו את הדירוג
       (אחרת "cheapest laptop" מקפיץ את "HP Laptop" רק בגלל המילה בשם) */
    "מחשב", "מחשבימ", "נייד", "ניידימ", "נייח", "ניידת", "לפטופ", "laptop", "notebook",
    "desktop", "computer", "מסכ", "monitor", "צג", "באנדל", "bundle", "מיני", "mini",
  ]);
  function nameHits(p, ctx) {
    if (!ctx) return 0;
    const hay = definalize((p.name + " " + (p.specs || "") + " " + (p.brand || "")).toLowerCase());
    let n = 0;
    for (const t of ctx.tokens) {
      if (t.length < 3 || STOP.has(t)) continue;
      // מנסים גם בלי תחילית ("ועכבר" → "עכבר")
      if (hay.includes(t) || (t.length > 3 && /^[ולבהמשכ]/.test(t) && hay.includes(t.slice(1)))) n++;
    }
    return n;
  }

  function fit(p, it) {
    let s = 0;
    const t = ptype(p);

    if (it.budget) {
      const r = p.price / it.budget;
      if (r <= 1) s += 45 * (0.45 + 0.55 * r);   // קרוב לתקציב = תמורה טובה יותר
      else s += 45 - (r - 1) * 300;               // מעל התקציב — עונש כבד
    }
    const pw = it.budget ? 0.3 : 1;               // אם יש תקציב מפורש, הוא הקובע
    if (it.pricePref === "low") s += pw * Math.max(0, 32 - p.price / 100);
    if (it.pricePref === "high") s += pw * Math.min(32, p.price / 260);

    if (it.use === "business" && /ThinkPad|EliteDesk|ProBook|Latitude|OptiPlex|ThinkCentre|EliteBook/i.test(p.name)) s += 14;
    if (it.use === "heavy" && isPerf(p)) s += 18;
    if (it.use === "gaming" && /i7|GPU|כרטיס מסך|Iris|4GB/i.test(p.specs || "")) s += 12;
    if ((it.use === "home" || it.use === "student") && p.price < 1800) s += 12;
    if (it.use === "student" && t === "laptop") s += 8;
    if (it.urgent && (p.status === "stock" || !p.status)) s += 6;

    if (p.wasPrice) s += 9;                        // במבצע = שווה להציף
    if (p.badge) s += 3;
    if (!it.type && t === "accessory") s -= 20;    // בלי בקשה מפורשת — אביזר לא מוביל
    s += 16 * nameHits(p, it.ctx);                 // הזכירו שם/דגם? זה מנצח
    return s;
  }

  function rank(it) {
    let pool = products().filter((p) => p.price > 0);
    const relaxed = [];

    /* סוג מוצר — סינון קשיח */
    if (it.type === "computer") pool = pool.filter((p) => ptype(p) === "laptop" || ptype(p) === "desktop");
    else if (it.type) pool = pool.filter((p) => ptype(p) === it.type);
    else pool = pool.filter((p) => ptype(p) !== "accessory");  // בלי סוג מפורש — לא מציעים כבלים

    /* שאר המסננים — מרפים אחד-אחד אם התוצאה מתרוקנת */
    const step = (fn, label) => {
      const next = pool.filter(fn);
      if (next.length) pool = next; else relaxed.push(label);
    };
    if (it.brand) step((p) => p.brand === it.brand, it.brand);
    if (it.cond === "used") step((p) => p.category === "יד שנייה", "יד שנייה");
    if (it.cond === "new") step((p) => p.category === "מחשבים חדשים", "חדש");
    if (it.specs) it.specs.forEach((sp) => step((p) => (p.specs || "").toUpperCase().includes(sp.toUpperCase()), sp));
    if (it.use === "heavy") step(isPerf, "ביצועים גבוהים");
    if (it.budget) {
      const cap = Math.round(it.budget * (it.approx ? 1.18 : 1.05));
      step((p) => p.price <= cap, "תקציב " + ils(it.budget));
    }

    /* "הכי זול" / "הכי חזק" = בקשה מפורשת לסדר לפי מחיר, בלי שיקולים אחרים */
    if (it.superlative === "low") pool = pool.slice().sort((a, b) => a.price - b.price);
    else if (it.superlative === "high") pool = pool.slice().sort((a, b) => b.price - a.price);
    else pool = pool.map((p) => ({ p, s: fit(p, it) })).sort((a, b) => b.s - a.s || a.p.price - b.p.price).map((x) => x.p);
    return { list: pool, relaxed };
  }

  /* ══════════════════════════════════════════════════════════
     7. תשובות ידע
     ══════════════════════════════════════════════════════════ */
  const KB = {
    shipping: () => `🚚 <b>משלוחים</b><br>
      • <b>משלוח חינם בכל קנייה</b> לכל הארץ — בלי מינימום.<br>
      • מוצרים במלאי: <b>2–5 ימי עסקים</b>.<br>
      • הזמנה מיוחדת: עד 14 ימי עסקים.<br>
      • <b>איסוף עצמי חינם</b> מ${BIZ.address} בתיאום מראש.<br>
      • השליח מתאם איתכם מועד מסירה מראש.<br>
      פרטים מלאים ב${link("shipping.html", "מדיניות המשלוחים")}.`,

    warranty: () => `🛡️ <b>אחריות</b><br>
      • <b>מוצרים חדשים</b> — אחריות יצרן/יבואן רשמי (12–36 חודשים לפי הדגם).<br>
      • <b>מוצרים מחודשים</b> — <b>אחריות ביג ברנדס ל-12 חודשים</b>, כולל חומרה, מערכת ההפעלה ותמיכה טכנית.<br>
      • ניתן להרחיב עד 24 חודשים בתוספת תשלום.<br>
      • זמן טיפול ממוצע בתקלה: 3–7 ימי עסקים.<br>
      יש תקלה? ${link(waLink("היי, יש לי תקלה במוצר שקניתי"), "פתחו קריאת שירות בוואטסאפ")} · ${link("warranty.html", "כל תנאי האחריות")}`,

    returns: () => `↩️ <b>ביטולים והחזרות</b><br>
      • <b>14 יום</b> להחזרה מיום קבלת המוצר (חוק הגנת הצרכן).<br>
      • אזרח ותיק / אדם עם מוגבלות / עולה חדש — עד <b>4 חודשים</b>.<br>
      • המוצר חוזר באריזה מקורית עם כל האביזרים.<br>
      • הגיע פגום או לא כמו שתואר? <b>ביטול ללא דמי ביטול וההובלה עלינו</b>.<br>
      • החזר כספי מלא תוך 14 יום לאמצעי התשלום המקורי.<br>
      ${link("returns.html", "מדיניות הביטולים המלאה")}`,

    payment: () => `💳 <b>תשלום</b><br>
      • כרטיסי אשראי, <b>Bit</b>, <b>PayBox</b>, העברה בנקאית ומזומן באיסוף עצמי.<br>
      • אפשרות לפריסה לתשלומים.<br>
      • חשבונית מס נשלחת לכל הזמנה — מתאים לעוסקים ולחברות.<br>
      • <b>כל המחירים באתר כוללים מע"מ</b> — המחיר שאתם רואים הוא המחיר הסופי.<br>
      רוצים שנבנה לכם הצעת מחיר? ${link(waLink("היי, אשמח להצעת מחיר"), "דברו איתנו")}`,

    vat: () => `🧾 <b>כל המחירים באתר כוללים מע"מ</b> — מה שאתם רואים זה מה שאתם משלמים.<br>
      אין עלויות נסתרות, והמשלוח חינם בכל קנייה. חשבונית מס נשלחת לכל הזמנה.`,

    refurb: () => `♻️ <b>מה זה "מחודש" בביג ברנדס?</b><br>
      אלה מחשבים <b>עסקיים</b> (ThinkPad, EliteDesk, Latitude, OptiPlex) שיצאו מחברות גדולות — בנויים לעבוד 24/7, הרבה יותר חזקים מדגמים ביתיים באותו מחיר.<br><br>
      <b>כל מחשב עובר אצלנו:</b><br>
      1. בדיקה מקיפה של כל הרכיבים<br>
      2. ניקוי פנימי והחלפת רכיבים תקולים<br>
      3. התקנה נקייה של Windows 11 מקורי<br>
      4. בדיקת עומסים סופית<br><br>
      ומקבל <b>אחריות ביג ברנדס ל-12 חודשים</b>. זה למה זה משתלם פי כמה ממחשב חדש זול.`,

    location: () => `📍 <b>איפה אנחנו</b><br>
      ${BIZ.address}<br>
      אפשר להגיע ל<b>איסוף עצמי</b> (חינם) בתיאום מראש, או שנשלח אליכם חינם לכל הארץ.<br>
      טלפון: ${link("tel:" + BIZ.phone, BIZ.phoneNice)}`,

    hours: () => `🕒 <b>זמינות</b><br>
      אנחנו זמינים בטלפון ובוואטסאפ בימים א׳–ה׳, ובשישי עד הצהריים.<br>
      הודעות בוואטסאפ נענות גם מחוץ לשעות — ${link(waLink("היי, אשמח לפרטים"), "כתבו לנו")} ונחזור אליכם.<br>
      ${link("tel:" + BIZ.phone, BIZ.phoneNice)} · ${BIZ.email}`,

    contact: () => `💬 <b>נשמח לדבר איתכם</b><br>
      • וואטסאפ: ${link(waLink("היי, הגעתי מהאתר ואשמח לעזרה 🙂"), "לחצו לפתיחת שיחה")}<br>
      • טלפון: ${link("tel:" + BIZ.phone, BIZ.phoneNice)}<br>
      • מייל: ${link("mailto:" + BIZ.email, BIZ.email)}<br>
      • כתובת: ${BIZ.address}`,

    os: () => `💻 <b>מערכת הפעלה ותוכנות</b><br>
      • כל המחשבים מגיעים עם <b>Windows 11</b> מותקן ומופעל (רוב הדגמים עם רישיון <b>Pro</b>).<br>
      • ההתקנה נקייה — בלי תוכנות מיותרות.<br>
      • רוצים Office? יש לנו <b>Microsoft Office 2019 Professional</b> ברישיון קבוע ב-250 ₪.<br>
      • צריכים Linux או קונפיגורציה מיוחדת? נתאים לכם לפני המשלוח.`,

    upgrade: () => `⚙️ <b>שדרוגים</b><br>
      רוב המחשבים שלנו תומכים בשדרוג זיכרון ואחסון — בחלקם יש חריץ RAM פנוי.<br>
      אנחנו יכולים לשדרג לפני המשלוח (זיכרון נוסף, SSD גדול יותר) — ${link(waLink("היי, אשמח לשדרג מחשב לפני משלוח"), "דברו איתנו לתמחור")}.<br>
      השדרוג לא פוגע באחריות.`,

    business: () => `🏢 <b>רכש לעסקים וארגונים</b><br>
      אנחנו מספקים לחברות, מתנ"סים ועסקים — כולל הצעות מחיר מסודרות, חשבונית מס והתקנה.<br>
      • מחירים מיוחדים לכמויות<br>
      • הגדרה מראש לפי דרישות ה-IT שלכם<br>
      • ליווי ותמיכה שוטפת<br>
      ${link(waLink("היי, אני מעוניין בהצעת מחיר לעסק"), "בקשת הצעת מחיר")}`,
  };

  /* ══════════════════════════════════════════════════════════
     8. ממשק
     ══════════════════════════════════════════════════════════ */
  let root, body, awaiting = null, greeted = false;
  const memory = { budget: null, type: null, brand: null, cond: null, use: null, pricePref: null };
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
            <input class="cbot-in" id="cbotIn" placeholder="למשל: מחשב לעסק עד 1500…" autocomplete="off" aria-label="הודעה" />
            <button class="cbot-send" type="submit" aria-label="שליחה"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/></svg></button>
          </form>
          <div class="cbot-hint">מופעל על ידי BIG BRANDS · המלצות מהמלאי בזמן אמת</div>
        </footer>
      </section>`;
    document.body.appendChild(root);
    body = root.querySelector("#cbotBody");
    root.querySelector("#cbotLaunch").addEventListener("click", open);
    root.querySelector("#cbotClose").addEventListener("click", close);
    root.querySelector("#cbotForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const el = root.querySelector("#cbotIn"); const v = el.value.trim();
      if (v) { userSay(v); el.value = ""; }
    });
  }

  function open() {
    document.documentElement.classList.add("cbot-open");
    if (!greeted) { greeted = true; setTimeout(greet, 250); }
    setTimeout(() => root.querySelector("#cbotIn").focus(), 400);
  }
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
    arr.forEach((c) => {
      const b = document.createElement("button"); b.className = "cbot-chip"; b.textContent = c;
      b.addEventListener("click", () => userSay(c)); wrap.appendChild(b);
    });
    body.appendChild(wrap); scroll();
  }
  function productCard(p) {
    const a = document.createElement("a"); a.className = "cbot-prod";
    a.href = "product.html?id=" + encodeURIComponent(p.id);
    a.innerHTML = `<img class="cbot-pimg" src="${esc(p.image || "")}" alt="" onerror="this.style.visibility='hidden'"/>
      <div class="cbot-pinfo"><div class="cbot-pname">${esc(p.name)}</div>
      <div class="cbot-pprice">${ils(p.price)}${p.wasPrice ? ` <span style="color:var(--text-faint);font-weight:600;font-size:.8em;text-decoration:line-through">${ils(p.wasPrice)}</span>` : ""}</div></div>`;
    body.appendChild(a); scroll();
  }
  function typing() {
    const row = document.createElement("div"); row.className = "cbot-row bot"; row.id = "cbotTyping";
    row.innerHTML = `<span class="cbot-mini"></span><div class="cbot-bub cbot-typing"><i></i><i></i><i></i></div>`;
    body.appendChild(row); scroll(); return row;
  }
  function botSay(fn, delay) {
    const t = typing();
    setTimeout(() => { t.remove(); fn(); }, delay || 520 + Math.random() * 420);
  }

  function greet() {
    botSay(() => {
      botBubble(`שלום 👋 אני העוזר החכם של <b>BIG BRANDS</b>. אני מכיר את כל המלאי, המחירים והתנאים — תשאלו אותי כל דבר.`);
      setTimeout(() => botSay(() => {
        botBubble(`אפשר לכתוב לי חופשי, למשל: <i>"מחשב נייד לעסק עד 1500"</i> או <i>"מה זה מחודש?"</i>`);
        chips(["המלצה לפי תקציב 💰", "מחשב לעסק 💼", "יד שנייה משתלם ♻️", "משלוח ואחריות 🚚", "דבר עם נציג 💬"]);
      }, 480), 480);
    }, 480);
  }

  /* ══════════════════════════════════════════════════════════
     9. תצוגת תוצאות
     ══════════════════════════════════════════════════════════ */
  function describe(it) {
    const bits = [];
    if (it.cond === "used") bits.push("יד שנייה");
    if (it.cond === "new") bits.push("חדש");
    if (it.type && TYPE_HE[it.type]) bits.push(TYPE_HE[it.type]);
    if (it.use === "business") bits.push("לעסק");
    if (it.use === "gaming") bits.push("לגיימינג");
    if (it.use === "student") bits.push("לסטודנטים");
    if (it.use === "home") bits.push("לבית");
    if (it.use === "heavy") bits.push("לעבודה כבדה");
    if (it.brand) bits.push(it.brand);
    if (it.specs) bits.push(it.specs.join(" + "));
    if (it.budget) bits.push("עד " + ils(it.budget));
    else if (it.pricePref === "low") bits.push("הכי משתלם");
    else if (it.pricePref === "high") bits.push("הכי חזק");
    return bits;
  }

  function resultsFor(it, introOverride) {
    const { list, relaxed } = rank(it);
    botSay(() => {
      if (!list.length) {
        if (it.use === "gaming") {
          botBubble(`כרגע אין מחשבי גיימינג מוכנים במלאי — אבל אנחנו <b>מרכיבים מחשב גיימינג מותאם</b> לפי התקציב שלכם. רוצים שנציג יחזור אליכם?`);
          chips(["דבר עם נציג 💬", "מה יש במלאי 🗂️"]);
          return;
        }
        botBubble(`לא מצאתי משהו שמתאים במדויק 😅 בואו ננסה אחרת — אולי נרחיב קצת את הטווח?`);
        chips(["מה יש במלאי 🗂️", "יד שנייה ♻️", "דבר עם נציג 💬"]);
        return;
      }

      const bits = describe(it);
      let intro = introOverride || (bits.length ? `הבנתי — ${bits.join(" · ")}. הנה מה שמצאתי:` : `הנה ההמלצות שלי:`);
      if (it.use === "gaming") intro = `לגיימינג רציני אנחנו <b>מרכיבים מחשב מותאם</b> לפי התקציב — דברו איתנו 💬<br>בינתיים, אלה הדגמים החזקים שיש במלאי:`;
      if (relaxed.length) intro += `<br><span style="opacity:.75;font-size:.9em">(לא היה בדיוק ${relaxed.join(" + ")}, אז הבאתי את הכי קרוב)</span>`;
      botBubble(intro);

      list.slice(0, 3).forEach(productCard);

      const extra = [];
      if (list.length > 3) extra.push("עוד אפשרויות ➕");
      extra.push("דבר עם נציג 💬");
      chips(extra);
      window.__cbotMore = list.slice(3);
    });
  }

  /* ══════════════════════════════════════════════════════════
     10. לוגיקת שיחה
     ══════════════════════════════════════════════════════════ */
  function mergeMemory(it) {
    ["budget", "type", "brand", "cond", "use", "pricePref"].forEach((k) => {
      if (it[k]) memory[k] = it[k];
      else if (memory[k]) it[k] = memory[k];
    });
    return it;
  }

  function catalogOverview() {
    const all = products().filter((p) => p.price > 0);
    const byCat = {};
    all.forEach((p) => { (byCat[p.category] = byCat[p.category] || []).push(p); });
    const rows = Object.keys(byCat).map((c) => {
      const arr = byCat[c].sort((a, b) => a.price - b.price);
      return `• <b>${c}</b> — ${arr.length} דגמים, החל מ-${ils(arr[0].price)}`;
    }).join("<br>");
    return `🗂️ <b>מה יש לנו בחנות</b><br>${rows}<br><br>לצפייה בכל הקטלוג ${link("products.html", "לחצו כאן")}, או ספרו לי מה אתם צריכים ואמליץ.`;
  }

  function userSay(text) {
    userBubble(text);
    const t = text.replace(/[💰💼♻️🚚💬🗂️➕🙂👋💸💻🖥️🖼️📦]/g, "").trim();

    /* המשך שאלת תקציב */
    if (awaiting === "budget") {
      awaiting = null;
      const m = t.replace(/,/g, "").match(/(\d{3,6})/);
      if (m) {
        const it = mergeMemory({ budget: parseInt(m[1]), ctx: normalize(t) });
        resultsFor(it, `מצוין! הנה הבחירות הכי טובות עד ${ils(parseInt(m[1]))}:`);
        return;
      }
    }

    const it = parse(t);

    /* — פקודות צ'יפים — */
    if (rx("^עוד אפשרויות").test(t) && window.__cbotMore && window.__cbotMore.length) {
      botSay(() => {
        botBubble(`בכיף, עוד כמה:`);
        window.__cbotMore.slice(0, 3).forEach(productCard);
        window.__cbotMore = window.__cbotMore.slice(3);
        chips(window.__cbotMore.length ? ["עוד אפשרויות ➕", "דבר עם נציג 💬"] : ["דבר עם נציג 💬"]);
      });
      return;
    }
    if (rx("^המלצה לפי תקציב|^תקציב$").test(t)) {
      awaiting = "budget";
      botSay(() => botBubble(`בכיף 💰 מה התקציב שלכם? (אפשר לכתוב סתם "1500" או "עד 2000")`));
      return;
    }

    /* — שאלת השוואה נייד מול נייח — */
    if (it.compare === "laptop-vs-desktop") {
      botSay(() => {
        botBubble(`שאלה מצוינת 🤔 קיצור התשובה:<br><br>
          💻 <b>נייד</b> — אם צריך לזוז איתו (בית↔משרד, לימודים, נסיעות). מגיע עם מסך ומקלדת מובנים.<br><br>
          🖥️ <b>נייח</b> — אם הוא נשאר במקום אחד. <b>מקבלים הרבה יותר ביצועים על אותו כסף</b>, קל לשדרג, ומחזיק יותר שנים. צריך להוסיף מסך ומקלדת (או לקחת באנדל שכולל הכל).<br><br>
          לדוגמה אצלנו: נייח i5 דור 8 ב-990 ₪ מול נייד באותו מחיר — הנייח יהיה מהיר יותר.<br>
          למה זה משמש אצלכם?`);
        chips(["לעבודה במשרד 💼", "לבית ולגלישה 🏠", "ללימודים 🎓", "באנדל שכולל הכל 📦"]);
      });
      return;
    }

    /* — ידע על החנות (קודם לכל, זו שאלה ולא חיפוש) — */
    if (it.topic === "catalog") { botSay(() => { botBubble(catalogOverview()); chips(["מחשב נייד 💻", "מחשב נייח 🖥️", "יד שנייה ♻️", "באנדל מלא 📦"]); }); return; }
    if (it.topic && KB[it.topic]) {
      const TOPIC_CHIP = {
        shipping: "משלוחים 🚚", warranty: "אחריות 🛡️", returns: "החזרות ↩️", payment: "תשלום 💳",
        refurb: "מה זה מחודש ♻️", location: "איפה אתם 📍", hours: "שעות פעילות 🕒",
        vat: 'מע"מ 🧾', os: "מערכת הפעלה 💻", upgrade: "שדרוגים ⚙️", business: "הצעת מחיר לעסק 🏢",
      };
      botSay(() => {
        botBubble(KB[it.topic]());
        const c = [];
        if (it.topic2 && TOPIC_CHIP[it.topic2]) c.push(TOPIC_CHIP[it.topic2]);  // שאלה שנייה שזוהתה
        if (it.topic === "refurb") c.push("הראה לי יד שנייה ♻️", "מחשב לעסק 💼");
        else if (it.topic !== "contact") c.push("המלצה לפי תקציב 💰", "דבר עם נציג 💬");
        chips(c);
      });
      return;
    }

    /* — שיחת חולין — */
    if (it.small === "bot") {
      botSay(() => { botBubble(`אני העוזר הדיגיטלי של BIG BRANDS 🤖 מכיר את כל המלאי, המחירים, המשלוחים והאחריות. לכל דבר שדורש בן אדם — אחבר אתכם לנציג מיד.`); chips(["מה יש במלאי 🗂️", "דבר עם נציג 💬"]); });
      return;
    }
    if (it.small === "howareyou") {
      botSay(() => { botBubble(`מעולה, תודה ששאלתם 😊 מוכן לעזור לכם למצוא מחשב. מה אתם מחפשים?`); chips(["מחשב לעסק 💼", "המלצה לפי תקציב 💰", "יד שנייה ♻️"]); });
      return;
    }
    if (it.small === "help") {
      botSay(() => {
        botBubble(`בשמחה 🙂 בואו נצמצם בשלוש שאלות:<br>1. <b>נייד או נייח?</b><br>2. <b>למה זה משמש?</b> (עסק / בית / לימודים / עבודה כבדה)<br>3. <b>מה התקציב?</b><br><br>אפשר גם לענות הכל במשפט אחד — אני אבין.`);
        chips(["מחשב נייד 💻", "מחשב נייח 🖥️", "מחשב לעסק 💼", "המלצה לפי תקציב 💰"]);
      });
      return;
    }
    if (it.small === "bye") { botSay(() => botBubble(`יאללה, יום מעולה! 👋 אנחנו כאן אם תצטרכו — ${link(waLink("היי, חזרתי מהאתר"), "וואטסאפ")}.`)); return; }
    if (it.small === "joke") { botSay(() => botBubble(`מחשב מחודש נכנס לבר... ויוצא עם אחריות ל-12 חודשים 😄<br>בואו נמצא לכם משהו — מה אתם צריכים?`)); return; }

    /* — כוונה מוצרית — */
    const solid = it.type || it.use || it.cond || it.brand || it.specs || it.superlative;
    const shopping = it.budget || it.pricePref || it.urgent || it.want;

    if (solid || (it.budget && (memory.type || memory.use))) { resultsFor(mergeMemory(it)); return; }

    /* יש תקציב/רמז קנייה אבל בלי סוג — שואלים שאלה ממוקדת */
    if (shopping) {
      mergeMemory(it);
      const lead = it.budget
        ? `סבבה, תקציב של עד ${ils(it.budget)} 👌 מה מתאים לכם?`
        : it.pricePref === "low"
        ? `אני איתכם על משתלם 💸 איזה סוג מוצר מעניין אתכם?`
        : it.urgent
        ? `אין בעיה, יש לנו מלאי זמין למשלוח מהיר 🚚 מה אתם צריכים?`
        : `בכיף! רק תגידו לי איזה סוג מוצר:`;
      botSay(() => { botBubble(lead); chips(["מחשב נייד 💻", "מחשב נייח 🖥️", "מסך 🖼️", "באנדל מלא 📦", "לא יודע — תעזור לי 🤔"]); });
      return;
    }

    /* — ברכות ותודות (אחרי הכוונות, כדי ש"היי אני צריך מחשב" לא ייתקע כאן) — */
    if (it.small === "greet") {
      botSay(() => { botBubble(`היי! 😊 מה אתם מחפשים היום?`); chips(["מחשב לעסק 💼", "יד שנייה ♻️", "המלצה לפי תקציב 💰", "מה יש במלאי 🗂️"]); });
      return;
    }
    if (it.small === "thanks") { botSay(() => botBubble(`שמחתי לעזור! 🙌 יש עוד משהו?`)); return; }

    /* — לא הבנתי — */
    botSay(() => {
      botBubble(`לא בטוח שתפסתי 🤔 אפשר לנסח אחרת, או לבחור מכאן:`);
      chips(["מה יש במלאי 🗂️", "מחשב לעסק 💼", "מחשב נייד 💻", "יד שנייה ♻️", "המלצה לפי תקציב 💰", "דבר עם נציג 💬"]);
    });
  }

  /* חשיפה לבדיקות/דיבוג — window.__cbot.parse("מחשב זול עד 1000") */
  window.__cbot = { parse, rank, normalize, ptype, describe };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
})();
