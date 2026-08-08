/*
  SITE CONTENT (seed data)
  ------------------------
  Product catalog rebuilt from the OS-TECH listing (new + refurbished
  computers, bundles, monitors, accessories). Specs are factual; images
  currently point to the source CDN — replace with your own product
  photos for production (see note from the assistant).

  Leave a product's `image` empty and a clean, category-aware graphic
  is drawn automatically by window.deviceGraphic().
*/

const _IMG = "https://snsruxcwdkgqkorsdssa.supabase.co/storage/v1/object/public/product-images/";

const _PRODUCTS = [
  /* ── יד שנייה (refurbished) ── */
  { id:"u1", brand:"Lenovo", series:"T", name:"Lenovo ThinkPad T14 Gen 2", category:"יד שנייה", status:"stock", price:1590, badge:"",
    desc:`מחשב נייד עסקי מחודש של Lenovo מסדרת ThinkPad T — קל, מהיר ואמין, אידיאלי לעבודה יומיומית ולמשימות משרדיות בבית ובעסק.`,
    specs:`14" FHD | Intel i5-1135G7 (דור 11) | 16GB RAM | 256GB SSD | Thunderbolt 4 | WiFi 6 | Win11`,
    image:_IMG+"1777019117802_zqgfqv24mqm.jpg" },
  { id:"u2", brand:"Lenovo", series:"X", name:"Lenovo ThinkPad X13 Gen 2", category:"יד שנייה", status:"stock", price:1632, badge:"",
    desc:`מחשב נייד קומפקטי (13 אינץ') וקל במיוחד מסדרת ThinkPad X — מושלם לניידות מלאה, לעבודה בדרכים ולסטודנטים.`,
    specs:`13.3" IPS | Intel Core דור 11 | 16GB RAM | 256GB SSD | ~1.24 ק"ג | USB-C`,
    image:_IMG+"1777018645588_x8a6jds05if.png" },
  { id:"u3", brand:"Lenovo", series:"T", name:"Lenovo ThinkPad T14 Gen 1", category:"יד שנייה", status:"stock", price:1299, badge:"",
    desc:`מחשב נייד עסקי איכותי מחודש של Lenovo — ביצועים יציבים ואמינים לעבודה שגרתית במחיר משתלם במיוחד.`,
    specs:`14" FHD IPS | Intel Core דור 10 | 16GB RAM | 256GB SSD | Thunderbolt 3 | Win11 Pro`,
    image:_IMG+"1777018513469_vlq03kow2r.jpg" },
  { id:"u4", brand:"Lenovo", series:"P", name:"Lenovo ThinkPad P14s Gen 2", category:"יד שנייה", status:"stock", price:2800, badge:"",
    desc:`תחנת עבודה ניידת מסדרת ThinkPad P — מעבד i7 חזק וכרטיס מסך ייעודי, מתאים לעריכת וידאו, גרפיקה ולעבודות מקצועיות תובעניות.`,
    specs:`14" FHD IPS | Intel i7-1185G7 | 16GB DDR4 | 512GB NVMe | כרטיס מסך 4GB | Thunderbolt 4 | Win11 Pro`,
    image:_IMG+"1776944820012_cy2yu90hivm.jpg" },
  { id:"u5", brand:"Lenovo", series:"L", name:"Lenovo ThinkPad L14 Gen 1", category:"יד שנייה", status:"stock", price:1190, badge:"",
    desc:`מחשב נייד עסקי מחודש מסדרת ThinkPad L — הכניסה הכי משתלמת למחשב עסקי, פתרון מצוין למשרד ולעבודה מהבית.`,
    specs:`14" FHD | Intel i5-10210U | 16GB DDR4 | 256GB NVMe | USB-C | HDMI | Win11 Pro`,
    image:_IMG+"1776944007661_nfx66f8ajmd.png" },
  { id:"u6", brand:"Lenovo", series:"ThinkCentre", name:"Lenovo ThinkCentre M900 (מחשב נייח)", category:"יד שנייה", status:"stock", price:700, badge:"",
    desc:`מחשב שולחני של Lenovo לעבודה משרדית שקטה ואמינה — תומך בשני מסכים ומתאים לתחנות עבודה עסקיות.`,
    specs:`מחשב שולחן | Intel דור 6 | עד 32GB RAM | אחסון SSD/HDD | תמיכה בצגים כפולים | עיצוב קומפקטי`,
    image:"https://www.pcnasdaq.co.il/wp-content/uploads/2026/03/image-30.jpg" },
  { id:"u7", brand:"Dell", name:"Dell Latitude 5430 (Core i7)", category:"יד שנייה", status:"stock", price:2299, badge:"",
    desc:`מחשב נייד עסקי מוביל של Dell עם מעבד i7 דור 11 ומקלדת עברית מלאה — הבחירה המקצועית לעסקים ולעבודה יומיומית תובענית.`,
    specs:`14" FHD (1920x1200) | Intel i7 דור 11 | 16GB DDR4 | 256GB NVMe | Iris Xe | Thunderbolt 4 | מקלדת עברית`,
    image:"assets/products/u7.png" },
  { id:"u8", brand:"Lenovo", series:"X", name:"Lenovo ThinkPad X13 Gen 2 (FHD+)", category:"יד שנייה", status:"stock", price:1650, badge:"",
    desc:`מחשב נייד קומפקטי ואיכותי מסדרת ThinkPad X — מסך גבוה במיוחד וקורא טביעת אצבע לאבטחה נוחה.`,
    specs:`IPS FHD (1920x1200) | 1.27 ק"ג | SSD NVMe | WiFi 6 | Thunderbolt 4 | קורא טביעת אצבע`,
    image:_IMG+"1775677691222_ge5tve2s5md.png" },
  { id:"u9", brand:"Lenovo", series:"ThinkCentre", name:"Lenovo ThinkCentre M93p (Mini)", category:"יד שנייה", status:"stock", price:550, badge:"",
    desc:`מחשב נייח מיני של Lenovo — קומפקטי, שקט וחסכוני, פתרון בסיסי מעולה לעבודה משרדית ולגלישה במחיר מצוין.`,
    specs:`Mini Desktop | Intel i5 דור 4 | 8GB DDR3 | 256GB SSD | USB 3.0 | Gigabit LAN | VGA/DisplayPort`,
    image:_IMG+"1775662486646_nix68yrvsbi.jpg" },
  { id:"u10", brand:"HP", name:"HP EliteDesk 800 G2 Mini", category:"יד שנייה", status:"stock", price:680, badge:"",
    desc:`מחשב נייח מיני של HP — קומפקטי, חסכוני באנרגיה, מתאים למשרד ולעבודה מהבית.`,
    specs:`מחשב נייח קומפקטי | Intel i5 דור 6 | עד 16GB RAM | עד 512GB SSD | HDMI | 4×USB 3.0 | Win11`,
    image:_IMG+"1775677751909_yb5zxlbvsxl.jpg" },
  { id:"u11", brand:"Lenovo", series:"T", name:"Lenovo ThinkPad T14 Gen 2 (Win11 Pro)", category:"יד שנייה", status:"stock", price:1537, wasPrice:1618, badge:"מבצע",
    desc:`מחשב נייד עסקי מחודש עם רישיון Windows 11 Pro מלא — מוכן לעבודה מהיום הראשון, ללא צורך בהתקנות.`,
    specs:`14" FHD IPS | Intel Core דור 11 | 16GB DDR4 (חריץ פנוי) | 256GB NVMe | Thunderbolt 4 | WiFi 6 | Win11 Pro`,
    image:_IMG+"1775662389261_9mjb9jirrf.avif" },
  { id:"u12", brand:"HP", name:"HP EliteDesk 800 G6 SFF (i5 דור 10)", category:"יד שנייה", status:"stock", price:1880, wasPrice:2490, badge:"מבצע חם",
    desc:`מחשב נייח עסקי מחודש של HP מסדרת EliteDesk 800 G6 — מעבד i5 דור 10 חזק, 16GB RAM ו-SSD NVMe מהיר. שקט, קומפקטי ואמין, אידיאלי למשרד ולעבודה מהבית. במחיר מבצע חד-פעמי — משתלם במיוחד לרכישה עכשיו. המחיר כולל מע"מ.`,
    specs:`מחשב נייח SFF | Intel Core i5-10500 | 16GB DDR4 | 256GB NVMe SSD | Intel UHD Graphics | Windows 11 Pro | אחריות ביג ברנדס 12 חודשים | המחיר כולל מע"מ`,
    image:"assets/products/u12.png" },

  /* ── מחשבים חדשים ── */
  { id:"n1", brand:"HP", name:"HP Laptop 14-ep1018nj (Core 7)", category:"מחשבים חדשים", status:"stock", price:2900, badge:"חדש",
    desc:`מחשב נייד חדש של HP עם מעבד מדור אחרון וסוללה ל-15 שעות — פתרון מעולה לעבודה יומיומית, ללימודים ולשימוש ביתי.`,
    specs:`14" Full HD (1920x1200) | Intel Core 7 120U | 16GB DDR5 | 512GB NVMe | Iris Xe | סוללה עד 15 שעות | Win11`,
    image:_IMG+"1776544931124_k4t5qw0oaj8.jpg" },
  { id:"n2", brand:"HP", name:`HP 250R 15.6" G9`, category:"מחשבים חדשים", status:"stock", price:2500, badge:"חדש",
    desc:`מחשב נייד 15.6 אינץ' חדש של HP במחיר שווה — עם אחריות יצרן מלאה ל-3 שנים.`,
    specs:`15.6" | Intel Core i5 | 16GB RAM | 512GB SSD | FreeDOS | אחריות HP ל-3 שנים`,
    image:_IMG+"1775662647887_bf3a7z5rd1b.webp" },
  { id:"n3", brand:"HP", name:"HP ProBook G11 (עסקי)", category:"מחשבים חדשים", status:"stock", price:2500, badge:"חדש",
    desc:`מחשב נייד עסקי חדש של HP עם רישיון Windows 11 Pro — פתרון בטוח, אמין ומקצועי לכל עסק.`,
    specs:`15.6" FHD | Intel Core דור 14 | 16GB RAM | 512GB SSD | USB-C + USB-A | קורא כרטיסי SD | Win11 Pro`,
    image:_IMG+"1775677915944_bxxr0mh9aul.jpeg" },
  { id:"n4", brand:"Apple", name:`Apple MacBook Pro 14" M5 Pro — Space Black`, category:"מחשבים חדשים", status:"stock", price:7990, badge:"חדש", mpn:"MGDR4HB/A",
    desc:`מחשב נייד מקצועי של Apple עם שבב M5 Pro החדש — ביצועים יוצאי דופן לעריכת וידאו, יצירה ופיתוח, בעיצוב אלגנטי.`,
    specs:`14" | Apple M5 Pro 15-Core CPU | 16-Core GPU | 24GB RAM | 1TB SSD | macOS | צבע: Space Black`,
    image:"assets/products/n4.png" },

  /* ── באנדלים ── */
  { id:"b1", brand:"HP", name:"באנדל מקצועי HP — מחשב + מסך + מקלדת ועכבר", category:"באנדלים", status:"stock", price:1075, wasPrice:1265, badge:"חיסכון 15%",
    desc:`חבילה מלאה להקמת עמדת עבודה — מחשב, מסך, מקלדת ועכבר יחד במחיר משתלם במיוחד, מוכן להפעלה מהיום הראשון.`,
    specs:`HP EliteDesk 800 G2 Mini + מסך MAG 24" + מקלדת ועכבר אלחוטיים Logitech MK270`,
    image:_IMG+"1775925449384_rao3c5o6cr.png" },
  { id:"b2", brand:"Lenovo", name:"באנדל לבית ולמשרד — מחשב + מסך + מקלדת ועכבר", category:"באנדלים", status:"stock", price:999, wasPrice:1135, badge:"חיסכון 12%",
    desc:`כל מה שצריך להקמת עמדת עבודה בבית או במשרד — במחיר של מחשב אחד. פתרון חסכוני ומעולה למשרד.`,
    specs:`לנובו ThinkCentre M93p + מסך MAG 24" + מקלדת ועכבר אלחוטיים Logitech MK270`,
    image:_IMG+"1775924579444_5ls1wq3uw2g.png" },

  /* ── מסכים ── */
  { id:"mon1", brand:"MAG", name:`מסך MAG 24"`, category:"מסכים", status:"stock", price:485, badge:"",
    desc:`מסך מחשב 24 אינץ' באיכות גבוהה — מתאים לעבודה משרדית, גלישה, סטרימינג ומשחקים קלים.`,
    specs:`מסך מחשב 24" מסדרת MAG | מתאים לעבודה ולמשחקים`,
    image:_IMG+"1775662049689_bdo8i6dzdn9.webp" },

  /* ── אביזרים ── */
  { id:"acc1", brand:"Logitech", name:"מקלדת ועכבר אלחוטיים Logitech MK270", category:"אביזרים", status:"stock", price:100, badge:"",
    desc:`מקלדת ועכבר אלחוטיים של Logitech — התקנה בשנייה עם דונגל USB יחיד, ללא כבלים מיותרים.`,
    specs:`חבילת מקלדת ועכבר אלחוטית | קומפקטית וקלה לשימוש`,
    image:_IMG+"1775900922253_yxov4gj939e.jpg" },
  { id:"acc2", brand:"Lenovo", name:"מטען Type-C מקורי לנובו", category:"אביזרים", status:"stock", price:165, badge:"",
    desc:`מטען Type-C מקורי של Lenovo — תואם למגוון רחב של דגמי ThinkPad ו-IdeaPad חדשים.`,
    specs:`מטען Type-C מקורי | תואם למגוון דגמי Lenovo`,
    image:_IMG+"1775678075176_in2iv6dg7je.jpg" },
  { id:"acc3", brand:"", name:"כבל HDMI", category:"אביזרים", status:"stock", price:25, badge:"",
    desc:`כבל HDMI איכותי לחיבור מחשב, לפטופ או קונסולה למסך או לטלוויזיה — תמיכה ב-Full HD ו-4K.`,
    specs:`כבל HDMI לחיבור מחשבים למסכים ולטלוויזיות`,
    image:_IMG+"1775661689818_q5rzmluvxuh.webp" },
  { id:"acc4", brand:"Microsoft", name:"Microsoft Office 2019 Professional", category:"אביזרים", status:"stock", price:250, badge:"",
    desc:`חבילת Office מלאה עם רישיון קבוע — Word, Excel, PowerPoint ו-Outlook לעבודה מקצועית לאורך שנים.`,
    specs:`חבילת Office 2019 Pro | Word, Excel, PowerPoint, Outlook ועוד`,
    image:_IMG+"1775661896121_rlc4605spae.webp" },
];

window.SITE_DATA = {
  categories: [
    "כל המוצרים",
    "מחשבים חדשים",
    "יד שנייה",
    "באנדלים",
    "מסכים",
    "אביזרים",
  ],

  heroSlides: [
    {
      image: "assets/banners/dell-latitude.png",
      fallbackImage: "assets/banners/asus-expertbook.png",
      alt: "DELL Latitude 5430 — הבחירה המקצועית לעסקים",
      link: "product.html?id=u7",
    },
    {
      image: "assets/banners/apple-macbook.png",
      fallbackImage: "assets/banners/asus-expertbook.png",
      alt: "Apple MacBook Pro M5 — הבחירה המקצועית לעסקים",
      link: "product.html?id=n4",
    },
  ],

  featured: [
    { tag: "הנמכר ביותר", productId: "u1" },
    { tag: "מומלץ לעסקים", productId: "u7" },
    { tag: "במבצע", productId: "u3" },
    { tag: "חדש בחנות", productId: "n3" },
    { tag: "באנדל משתלם", productId: "b1" },
    { tag: "למשרד הקומפקטי", productId: "u10" },
  ],

  brands: ["Lenovo", "HP", "Dell", "ASUS"],

  partners: [
    {
      name: "פיצה האט",
      logo: "Pizza",
      image: "assets/partners/pizza.png",
      quote:
        "אנחנו עובדים עם BIG BRANDS למעלה מ-10 שנים. הם תמיד שם בנעימות ובמהירות, ומעניקים מענה מקצועי לכל בקשה.",
      person: "טל ליברמן · מנהל טכני",
    },
    {
      name: "דרך היין",
      logo: "Wine",
      image: "assets/partners/wine.png",
      quote:
        "שירות אישי ומקצועי לאורך כל הדרך. ליווי מלא מהאפיון ועד ההתקנה בכל הסניפים.",
      person: "ערן לוין · סמנכ\"ל",
    },
    {
      name: "ePost",
      logo: "Post",
      image: "assets/partners/post.png",
      quote:
        "אמינות מלאה, מחירים הוגנים ושירות שלא מאכזב. שותפים אמיתיים לעסק.",
      person: "דרור קריסי · מנכ\"ל",
    },
  ],

  products: _PRODUCTS,
};

/* ── Products that have an interactive 3D model at assets/models/{id}.glb ── */
window.MODELS_3D = ["u7"]; // Dell Latitude 5420 (carried over from the old l9 model)

/* ── Category-aware product graphic (shared by all pages) ──────────
   Returns clean SVG markup tinted with the brand accent. */
window.deviceGraphic = function (accent, category) {
  accent = accent || "#1f7ae0";
  const c = category || "";
  const gid = "g-" + Math.random().toString(36).slice(2, 8);
  const grad = `<defs><linearGradient id="${gid}" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="${accent}"/><stop offset="1" stop-color="#0a1f44"/></linearGradient></defs>`;
  const open = (label) => `<svg class="device" viewBox="0 0 240 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${label}">${grad}`;

  let type = "laptop";
  if (/אוזני|headphone|audio/.test(c)) type = "headphones";
  else if (/נייח|גיימינג|desktop/.test(c)) type = "desktop";
  else if (/gpu|כרטיס מסך/.test(c)) type = "gpu";
  else if (/רכיב|cpu|ram|component/.test(c)) type = "chip";
  else if (/סורק|scan/.test(c)) type = "scanner";
  else if (/מקרן|projector/.test(c)) type = "projector";
  else if (/דיו|מתכל|ink|toner/.test(c)) type = "ink";
  else if (/מדפס|קופ|pos|תווי|print/.test(c)) type = "printer";

  switch (type) {
    case "headphones":
      return open("אוזניות") + `
        <path d="M58 102V90a62 62 0 0 1 124 0v12" fill="none" stroke="url(#${gid})" stroke-width="13" stroke-linecap="round"/>
        <rect x="44" y="96" width="34" height="52" rx="14" fill="#1b2330"/>
        <rect x="50" y="102" width="22" height="40" rx="10" fill="url(#${gid})"/>
        <rect x="162" y="96" width="34" height="52" rx="14" fill="#1b2330"/>
        <rect x="168" y="102" width="22" height="40" rx="10" fill="url(#${gid})"/></svg>`;
    case "desktop":
      return open("מחשב נייח") + `
        <rect x="50" y="20" width="140" height="88" rx="9" fill="#1b2330"/>
        <rect x="57" y="27" width="126" height="74" rx="5" fill="url(#${gid})"/>
        <rect x="66" y="40" width="46" height="7" rx="3.5" fill="rgba(255,255,255,.9)"/>
        <rect x="66" y="54" width="74" height="6" rx="3" fill="rgba(255,255,255,.5)"/>
        <rect x="108" y="108" width="24" height="18" fill="#aeb8c9"/>
        <rect x="84" y="126" width="72" height="10" rx="5" fill="#cfd6e2"/></svg>`;
    case "gpu":
      return open("כרטיס מסך") + `
        <rect x="34" y="50" width="172" height="64" rx="12" fill="#1b2330"/>
        <rect x="34" y="50" width="172" height="64" rx="12" fill="url(#${gid})" opacity=".22"/>
        <circle cx="88" cy="82" r="23" fill="#0f1626" stroke="url(#${gid})" stroke-width="4"/>
        <circle cx="152" cy="82" r="23" fill="#0f1626" stroke="url(#${gid})" stroke-width="4"/>
        <circle cx="88" cy="82" r="6" fill="url(#${gid})"/><circle cx="152" cy="82" r="6" fill="url(#${gid})"/>
        <rect x="46" y="114" width="54" height="12" rx="2" fill="#aeb8c9"/></svg>`;
    case "chip":
      return open("רכיב מחשב") + `
        <rect x="76" y="46" width="88" height="88" rx="12" fill="#1b2330"/>
        <rect x="88" y="58" width="64" height="64" rx="7" fill="url(#${gid})"/>
        <rect x="96" y="66" width="48" height="48" rx="4" fill="#0f1626" opacity=".35"/>
        ${[0,1,2,3].map(i=>`<rect x="${92+i*18}" y="34" width="8" height="12" rx="2" fill="#9aa6bd"/><rect x="${92+i*18}" y="134" width="8" height="12" rx="2" fill="#9aa6bd"/>`).join("")}
        ${[0,1,2,3].map(i=>`<rect x="62" y="${58+i*18}" width="12" height="8" rx="2" fill="#9aa6bd"/><rect x="166" y="${58+i*18}" width="12" height="8" rx="2" fill="#9aa6bd"/>`).join("")}</svg>`;
    case "scanner":
      return open("סורק") + `
        <rect x="70" y="34" width="100" height="46" rx="4" fill="#fff" stroke="#cfd6e2" stroke-width="2"/>
        <rect x="82" y="48" width="64" height="5" rx="2.5" fill="url(#${gid})"/>
        <rect x="82" y="59" width="76" height="4" rx="2" fill="#c4ccd9"/>
        <rect x="40" y="80" width="160" height="44" rx="10" fill="#1b2330"/>
        <rect x="56" y="98" width="128" height="6" rx="3" fill="url(#${gid})"/></svg>`;
    case "projector":
      return open("מקרן") + `
        <path d="M104 74 L198 54 L198 126 L104 106 Z" fill="url(#${gid})" opacity=".16"/>
        <rect x="44" y="62" width="118" height="56" rx="14" fill="#1b2330"/>
        <circle cx="80" cy="90" r="21" fill="#0f1626" stroke="url(#${gid})" stroke-width="5"/>
        <circle cx="80" cy="90" r="9" fill="url(#${gid})"/>
        <rect x="120" y="70" width="22" height="6" rx="3" fill="#c4ccd9"/></svg>`;
    case "ink":
      return open("דיו / מתכלה") + `
        <rect x="84" y="42" width="72" height="96" rx="10" fill="#1b2330"/>
        <rect x="84" y="42" width="72" height="52" rx="10" fill="url(#${gid})"/>
        <rect x="100" y="32" width="40" height="16" rx="4" fill="#2a3550"/>
        <path d="M120 96 c-9 11 -9 19 0 23 c9 -4 9 -12 0 -23z" fill="#fff" opacity=".9"/></svg>`;
    case "printer":
      return open("מדפסת") + `
        <rect x="66" y="34" width="108" height="30" rx="3" fill="#fff" stroke="#cfd6e2" stroke-width="2"/>
        <rect x="44" y="60" width="152" height="60" rx="12" fill="#1b2330"/>
        <rect x="44" y="60" width="152" height="22" rx="12" fill="url(#${gid})" opacity=".3"/>
        <circle cx="170" cy="92" r="5" fill="url(#${gid})"/>
        <rect x="66" y="116" width="108" height="20" rx="3" fill="#fff" stroke="#cfd6e2" stroke-width="2"/></svg>`;
    default: // laptop
      return open("מחשב נייד") + `
        <rect x="50" y="18" width="140" height="90" rx="9" fill="#1b2330"/>
        <rect x="57" y="25" width="126" height="76" rx="5" fill="url(#${gid})"/>
        <rect x="66" y="38" width="48" height="7" rx="3.5" fill="rgba(255,255,255,.9)"/>
        <rect x="66" y="52" width="78" height="6" rx="3" fill="rgba(255,255,255,.55)"/>
        <rect x="66" y="64" width="60" height="6" rx="3" fill="rgba(255,255,255,.38)"/>
        <path d="M32 108h176l12 20a5 5 0 0 1-5 7H25a5 5 0 0 1-5-7z" fill="#cfd6e2"/>
        <rect x="98" y="114" width="44" height="6" rx="3" fill="#9aa6bd"/></svg>`;
  }
};
