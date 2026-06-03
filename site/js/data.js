/*
  SITE CONTENT (seed data)
  ------------------------
  Replaceable data layer. The catalog below is imported from the
  KTWO dealer price list (June 2026). Each raw item is mapped into the
  storefront product schema by _toProduct().  Prices are the dealer
  figures from the catalog (before VAT) — adjust in the admin if needed.

  Leave a product's `image` empty and a clean, category-aware graphic
  is drawn automatically by window.deviceGraphic().
*/

/* ── RAW CATALOG (verbatim from Master_Catalog_JUNE) ───────────── */
const _laptops = [
  { id:'l1', brand:'Lenovo', name:'ThinkPad X1 Yoga Gen 6', spec:'i5-1145G7 | 16GB | 256GB | 14" FHD Touch | Win11', dealer:1700, status:'stock' },
  { id:'l2', brand:'Lenovo', name:'ThinkPad T14s Gen 2', spec:'i5-1135G7 | 16GB | 256GB | 14" FHD | Win11', dealer:1480, status:'stock' },
  { id:'l3', brand:'Lenovo', name:'ThinkPad T14s Gen 1', spec:'i5-10210U | 16GB | 256GB | 14" FHD | Win11', dealer:1350, status:'stock' },
  { id:'l4', brand:'Lenovo', name:'ThinkPad X13 Yoga Gen 1', spec:'i5-10310U | 16GB | 256GB | 13.3" FHD Touch | Win11', dealer:1450, status:'stock' },
  { id:'l5', brand:'Lenovo', name:'ThinkPad X1 Carbon Gen 9', spec:'i5-1145G7 | 16GB | 256GB | 14" FHD | Win11', dealer:1650, status:'stock' },
  { id:'l6', brand:'HP', name:'ProBook X360 13.3"', spec:'Ryzen 7 5800U | 16GB | 256GB | Win11 | Convertible', dealer:1480, status:'stock' },
  { id:'l7', brand:'HP', name:'ProBook 445 G8', spec:'Ryzen 5 5600U | 8GB | 256GB | Win11', dealer:1130, status:'stock' },
  { id:'l8', brand:'Dell', name:'Latitude 7420', spec:'i5-1145G7 דור 11 | 16GB | 256GB | Win11', dealer:1270, status:'stock' },
  { id:'l9', brand:'Dell', name:'Latitude 5420 (8GB)', spec:'i5-1135G7 | 8GB | 256GB | Win11', dealer:1130, status:'stock' },
  { id:'l10', brand:'Dell', name:'Latitude 5420 (16GB)', spec:'i7-1165G7 | 16GB | 256GB | Win11', dealer:1350, status:'stock' },
];

const _desktops = [
  { id:'d1', brand:'HP', name:'EliteDesk 800 G4 DM', spec:'i5-8500T | 8GB | 256GB | Win11', dealer:808, status:'stock', code:'HP-800-G4-I5-8GB-256-DM' },
  { id:'d2', brand:'HP', name:'EliteDesk 800 G5 DM', spec:'i5-9500T | 16GB | 256GB | Win11', dealer:1051, status:'stock', code:'HP-800-G5-I5-16GB-256-DM' },
  { id:'d3', brand:'HP', name:'EliteDesk 800 G6 DM (16GB)', spec:'i5-10500T | 16GB | 256GB | Win11', dealer:1376, status:'stock', stock:'מלאי גדול!', code:'HP-800-G6-I5-16GB-256-DM', hot:true },
  { id:'d4', brand:'HP', name:'EliteDesk 800 G6 DM (8GB)', spec:'i5-10500T | 8GB | 256GB | Win11', dealer:1254, status:'stock', code:'HP-800-G6-I5-8GB-256-DM' },
  { id:'d5', brand:'HP', name:'EliteDesk 800 G5 SFF', spec:'i5-9500 | 16GB | 256GB | Win11', dealer:1072, status:'stock', stock:"110 יח'", code:'HP-800G5-SFF-I5-16-256' },
  { id:'d6', brand:'HP', name:'EliteDesk 600 G9 DM', spec:'i5 Gen 12 | 16GB | 256GB | Win11', dealer:1650, status:'stock', stock:"100 יח'", code:'HP-600-G9-DM-I5-16-256' },
  { id:'d7', brand:'HP', name:'HP 800G6 DM 35W', spec:'i5-10500T | 8GB | 256GB | Win11', dealer:1100, status:'stock' },
  { id:'d8', brand:'HP', name:'HP 800 G9 DM', spec:'i5-13500 | 16GB | 256GB | Win11', dealer:1600, status:'stock' },
  { id:'d9', brand:'Lenovo', name:'ThinkCentre M920Q Tiny (8GB)', spec:'i5-8500T | 8GB | 256GB | Win11', dealer:800, status:'stock', code:'LO-M920Q-Tiny-582' },
  { id:'d10', brand:'Lenovo', name:'ThinkCentre M920Q Tiny (16GB)', spec:'i5-8500T | 16GB | 256GB | Win11', dealer:835, status:'stock', code:'LO-M920Q-Tiny-5162' },
  { id:'d11', brand:'Lenovo', name:'ThinkCentre M70Q Gen 3 Tiny', spec:'i5-12500T | 16GB | 256GB | Win11', dealer:1274, status:'stock', stock:"30 יח'", code:'LO-M70Q-G3-I5-16-256' },
  { id:'d12', brand:'Lenovo', name:'M920X Tiny', spec:'i5-8600T | 8GB | 256GB | Win11', dealer:700, status:'stock' },
];

const _gaming = [
  { id:'g1', brand:'Antec/ASUS', name:'Gaming Desktop', spec:'i7-12700F | RTX 3050 8GB | 32GB DDR5 | 1TB NVMe | Win11', dealer:3900, status:'new' },
];

const _components = [
  { id:'c1', brand:'Intel', name:'Core i5-12400F', spec:'Alder Lake | 6C/12T | LGA1700 | No iGPU', dealer:600, status:'stock' },
  { id:'c2', brand:'Intel', name:'Core i7-12700F', spec:'Alder Lake | 12C/20T | LGA1700 | No iGPU', dealer:1192, status:'stock' },
  { id:'c3', brand:'ASUS', name:'Prime B610M-K ARGB', spec:'LGA1700 | B610 | DDR5 | mATX | ARGB', dealer:355, status:'stock' },
  { id:'c4', brand:'Generic', name:'16GB DDR5-5600 RGB', spec:'DDR5 | 5600MHz | 1×16GB | RGB', dealer:907, status:'stock' },
  { id:'c5', brand:'ANTEC', name:'VX Series (Case + PSU)', spec:'Mid-Tower | Bundled PSU | Entry-Level Gaming', dealer:304, status:'stock' },
  { id:'c6', brand:'Generic', name:'1TB NVMe SSD', spec:'M.2 PCIe | Gen 3/4 | 1000GB', dealer:653, status:'stock' },
];

const _gpuItems = [
  { id:'gpu1', brand:'NVIDIA/Palit', name:'RTX 3050 PEGASUS', spec:'6GB GDDR6 | NE63050018JE-1072E', dealer:787, status:'request' },
  { id:'gpu2', brand:'NVIDIA/Palit', name:'RTX 5050 GHOST RGB', spec:'8GB GDDR6 | NE65050019P1-GB2070B', dealer:1071, status:'stock' },
  { id:'gpu3', brand:'NVIDIA/Palit', name:'RTX 5060 GHOST RGB', spec:'8GB GDDR7 | NE75060019P1-GB2063B', dealer:1196, status:'stock', hot:true },
  { id:'gpu4', brand:'NVIDIA/Palit', name:'RTX 5060 Ti PYTHON III OC', spec:'16GB GDDR7 | NE7506TS19T1-GB2061T', dealer:2049, status:'stock' },
  { id:'gpu5', brand:'NVIDIA/Palit', name:'RTX 5070 PYTHON III', spec:'12GB GDDR7 | NE75070019K9-GB2050T', dealer:2204, status:'stock' },
  { id:'gpu6', brand:'NVIDIA/Palit', name:'RTX 5070 Ti PHOENIX-S GS', spec:'16GB GDDR7 | NE7507TS19T2-GB2031K', dealer:3393, status:'request' },
  { id:'gpu7', brand:'NVIDIA/Palit', name:'RTX 5080 PHOENIX', spec:'16GB GDDR7 | NE75080019T2-GB2031X', dealer:4302, status:'request' },
];

const _epsonScanners = [
  { id:'es1', brand:'Epson', name:'WorkForce DS-790WN', spec:'סורק רשת | A4 | Duplex | 45ppm | WiFi', dealer:1900, status:'limited', mpn:'B11B265401' },
  { id:'es2', brand:'Epson', name:'WorkForce DS-1630', spec:'סורק שטוח + ADF | A3 | USB | 25ppm', dealer:1140, status:'request', mpn:'B11B256401' },
  { id:'es3', brand:'Epson', name:'WorkForce DS-870', spec:'סורק מסמכים | A4 | Duplex | 65ppm | USB+LAN', dealer:2620, status:'request', mpn:'B11B236201' },
  { id:'es4', brand:'Epson', name:'FastFoto FF-580', spec:'סורק תמונות | 4×6 | USB | 200dpi', dealer:2220, status:'request', mpn:'B11B248401' },
  { id:'es5', brand:'Epson', name:'Perfection V850 Pro (13000XL)', spec:'סורק שטוח מקצועי | A4 | 6400dpi | USB', dealer:17860, status:'request', mpn:'B11B198011' },
  { id:'es6', brand:'Epson', name:'WorkForce DS-6500', spec:'סורק מסמכים | A3 | Duplex | 45ppm | USB+LAN', dealer:4250, status:'request', mpn:'B11B207221' },
  { id:'es7', brand:'Epson', name:'WorkForce DS-32000', spec:'סורק תעשייתי | A3 | Duplex | 100ppm | LAN', dealer:14290, status:'request', mpn:'B11B256701' },
];

const _brotherScanners = [
  { id:'bs1', brand:'Brother', name:'ADS-4100W', spec:'סורק מסמכים | A4 | Duplex | WiFi | 40ppm', dealer:1150, status:'stock', stock:"50 יח'", mpn:'ADS-4100W' },
  { id:'bs2', brand:'Brother', name:'ADS-4300W', spec:'סורק מסמכים | A4 | Duplex | WiFi | NFC | 40ppm', dealer:1500, status:'stock', stock:"50 יח'", mpn:'ADS-4300W' },
  { id:'bs3', brand:'Brother', name:'ADS-4700W', spec:'סורק מסמכים | A4 | Duplex | WiFi | Touch | 60ppm', dealer:2200, status:'stock', stock:"50 יח'", mpn:'ADS-4700W', hot:true },
  { id:'bs4', brand:'Brother', name:'ADS-4900W', spec:'סורק מסמכים | A4 | Duplex | WiFi | Touch | 80ppm', dealer:3000, status:'stock', stock:"50 יח'", mpn:'ADS-4900W' },
];

const _workforce = [
  { id:'wf1', brand:'Epson', name:'WF-C5890DWF', spec:'WorkForce Pro Color | 4-in-1 | A4 | Duplex | Fax | WiFi', dealer:1890, status:'request', bundle:'באנדל + סט דיו: ₪2,420', mpn:'C11CK23401' },
  { id:'wf2', brand:'Epson', name:'WF-C5390DW', spec:'WorkForce Pro Color | 4-in-1 | A4 | Duplex | WiFi', dealer:1399, status:'request', bundle:'באנדל + סט דיו: ₪2,080', mpn:'C11CK25401' },
  { id:'wf3', brand:'Epson', name:'WF-M5899DWF', spec:'WorkForce Pro B&W | 4-in-1 | A4 | Duplex | Fax | WiFi', dealer:1250, status:'request', bundle:'באנדל + דיו: ₪1,500', mpn:'C11CK76401' },
  { id:'wf4', brand:'Epson', name:'WF-M5399DW', spec:'WorkForce Pro B&W | מדפסת | A4 | Duplex | WiFi', dealer:799, status:'request', bundle:'באנדל + דיו: ₪990', mpn:'C11CK77401' },
];

const _pos = [
  { id:'pos1', brand:'Epson', name:'TM-T88VII (112)', spec:'POS Printer | USB+ETH+Serial | 80mm | שחור', dealer:700, status:'stock', stock:"500 יח'", mpn:'C31CJ57112' },
  { id:'pos2', brand:'Epson', name:'TM-T20III (012)', spec:'POS Printer | Ethernet | 80mm | שחור', dealer:400, status:'stock', stock:"500 יח'", mpn:'C31CH51012' },
  { id:'pos3', brand:'Epson', name:'TM-m30III (112)', spec:'POS Printer | USB+ETH | 80mm | שחור', dealer:620, status:'request', mpn:'C31CK50112' },
  { id:'pos4', brand:'SNBC', name:'BTP-R880NP', spec:'POS Printer | USB+ETH+Serial | 80mm', dealer:650, status:'request', mpn:'SNBC-R880NP' },
  { id:'pos5', brand:'Epson', name:'מגירת כסף לקופה', spec:'RJ11 | 5 שטרות / 8 מטבעות', dealer:240, status:'request', mpn:'CASH-DRAWER' },
];

const _projectors = [
  { id:'pr1', brand:'Epson', name:'EH-TW5825', spec:'מקרן קולנוע ביתי Full HD 1080p | 3,400 לומן | WiFi 5 + AirPlay 2', dealer:3150, status:'stock', mpn:'V11HB61042' },
  { id:'pr2', brand:'Epson', name:'EH-TW6250', spec:'מקרן 4K PRO-UHD | WiFi | Android TV', dealer:4500, status:'stock', mpn:'V11HA73040' },
];

const _colorLabelPrinters = [
  { id:'cl1', brand:'Epson', name:'CW-C4000e (BK)', spec:'Color Label Printer | Black Ink Model', dealer:5423, status:'request', mpn:'C31CK03102BK' },
  { id:'cl2', brand:'Epson', name:'CW-C4000e (MK)', spec:'Color Label Printer | Matte Black Ink Model', dealer:5423, status:'request', mpn:'C31CK03102MK' },
  { id:'cl3', brand:'Epson', name:'CW-C6000Ae ללא פילר', spec:'ColorWorks | Color Label Printer | Without Peeler', dealer:7038, status:'request', mpn:'C31CH76102' },
  { id:'cl4', brand:'Epson', name:'CW-C6000Ae עם פילר', spec:'ColorWorks | Color Label Printer | With Peeler', dealer:7397, status:'request', mpn:'C31CH76102P' },
  { id:'cl5', brand:'Epson', name:'CW-C6500Ae ללא פילר', spec:'ColorWorks | Color Inkjet Label Printer | Without Peeler', dealer:8632, status:'request', mpn:'C31CH77102' },
  { id:'cl6', brand:'Epson', name:'CW-C6500Ae עם פילר', spec:'ColorWorks | Color Inkjet Label Printer | With Peeler', dealer:12161, status:'request', mpn:'C31CH77102P' },
  { id:'cl7', brand:'Epson', name:'CW-C8000e (BK) ללא פילר', spec:'ColorWorks | High-Speed Color Label Printer | Black Ink', dealer:20966, status:'request', mpn:'C31CL02102BK' },
  { id:'cl8', brand:'Epson', name:'CW-C8000e (MK) ללא פילר', spec:'ColorWorks | High-Speed Color Label Printer | Matte Black', dealer:20966, status:'request', mpn:'C31CL02102MK' },
];

const _colorLabelInk = [
  { id:'cli1', brand:'Epson', name:'C4000e דיו שחור (BK)', spec:'Ink Cartridge Black | CW-C4000e', dealer:107, status:'request', mpn:'C13T52M140' },
  { id:'cli2', brand:'Epson', name:'C4000e דיו ציאן', spec:'Ink Cartridge Cyan | CW-C4000e', dealer:107, status:'request', mpn:'C13T52M240' },
  { id:'cli3', brand:'Epson', name:'C4000e דיו מגנטה', spec:'Ink Cartridge Magenta | CW-C4000e', dealer:107, status:'request', mpn:'C13T52M340' },
  { id:'cli4', brand:'Epson', name:'C4000e דיו צהוב', spec:'Ink Cartridge Yellow | CW-C4000e', dealer:107, status:'request', mpn:'C13T52M440' },
  { id:'cli5', brand:'Epson', name:'C4000e דיו שחור מט (MK)', spec:'Ink Cartridge Matte Black | CW-C4000e MK', dealer:107, status:'request', mpn:'C13T52M540' },
  { id:'cli6', brand:'Epson', name:'C4000e Maintenance Box', spec:'Maintenance Box | CW-C4000e', dealer:93, status:'request', mpn:'C33S021601' },
  { id:'cli7', brand:'Epson', name:'C6000/C6500 דיו שחור', spec:'Ink Cartridge Black | ColorWorks C6000/C6500', dealer:138, status:'request', mpn:'C13T44C140' },
  { id:'cli8', brand:'Epson', name:'C6000/C6500 דיו ציאן', spec:'Ink Cartridge Cyan | ColorWorks C6000/C6500', dealer:138, status:'request', mpn:'C13T44C240' },
  { id:'cli9', brand:'Epson', name:'C6000/C6500 דיו מגנטה', spec:'Ink Cartridge Magenta | ColorWorks C6000/C6500', dealer:138, status:'request', mpn:'C13T44C340' },
  { id:'cli10', brand:'Epson', name:'C6000/C6500 דיו צהוב', spec:'Ink Cartridge Yellow | ColorWorks C6000/C6500', dealer:138, status:'request', mpn:'C13T44C440' },
  { id:'cli11', brand:'Epson', name:'C6000/C6500 Maintenance Box', spec:'Maintenance Box | ColorWorks C6000/C6500', dealer:90, status:'request', mpn:'C33S021501' },
  { id:'cli12', brand:'Epson', name:'C8000e דיו שחור (BK)', spec:'SJIC48P-BK Black Ink | CW-C8000e', dealer:787, status:'request', mpn:'C13T55P140' },
  { id:'cli13', brand:'Epson', name:'C8000e דיו ציאן', spec:'SJIC48P-C Cyan Ink | CW-C8000e', dealer:787, status:'request', mpn:'C13T55P240' },
  { id:'cli14', brand:'Epson', name:'C8000e דיו מגנטה', spec:'SJIC48P-M Magenta Ink | CW-C8000e', dealer:787, status:'request', mpn:'C13T55P340' },
  { id:'cli15', brand:'Epson', name:'C8000e דיו צהוב', spec:'SJIC48P-Y Yellow Ink | CW-C8000e', dealer:787, status:'request', mpn:'C13T55P440' },
  { id:'cli16', brand:'Epson', name:'C8000e דיו שחור מט (MK)', spec:'SJIC48P-MK Matte Black Ink | CW-C8000e', dealer:787, status:'request', mpn:'C13T55P540' },
  { id:'cli17', brand:'Epson', name:'C8000/C7500 Maintenance Box', spec:'Maintenance Box | ColorWorks C7500/C7500G/C8000', dealer:97, status:'request', mpn:'C33S020596' },
  { id:'cli18', brand:'Epson', name:'TU-RC8000', spec:'Roll Cutter | CW-C8000e', dealer:1777, status:'request', mpn:'C32C882501' },
  { id:'cli19', brand:'Epson', name:'C7500 דיו שחור', spec:'Ink Cartridge Black | ColorWorks C7500', dealer:493, status:'request', mpn:'C33S020618' },
  { id:'cli20', brand:'Epson', name:'C7500 דיו ציאן', spec:'Ink Cartridge Cyan | ColorWorks C7500', dealer:493, status:'request', mpn:'C33S020619' },
  { id:'cli21', brand:'Epson', name:'C7500 דיו מגנטה', spec:'Ink Cartridge Magenta | ColorWorks C7500', dealer:493, status:'request', mpn:'C33S020620' },
  { id:'cli22', brand:'Epson', name:'C7500 דיו צהוב', spec:'Ink Cartridge Yellow | ColorWorks C7500', dealer:493, status:'request', mpn:'C33S020621' },
  { id:'cli23', brand:'Epson', name:'C7500G דיו שחור', spec:'Ink Cartridge Black | ColorWorks C7500G', dealer:493, status:'request', mpn:'C33S020639' },
  { id:'cli24', brand:'Epson', name:'C7500G דיו ציאן', spec:'Ink Cartridge Cyan | ColorWorks C7500G', dealer:493, status:'request', mpn:'C33S020640' },
  { id:'cli25', brand:'Epson', name:'C7500G דיו מגנטה', spec:'Ink Cartridge Magenta | ColorWorks C7500G', dealer:493, status:'request', mpn:'C33S020641' },
  { id:'cli26', brand:'Epson', name:'C7500G דיו צהוב', spec:'Ink Cartridge Yellow | ColorWorks C7500G', dealer:493, status:'request', mpn:'C33S020642' },
];

const _consumables = [
  { id:'con1', brand:'Epson', name:'דיו שחור 5K', spec:'עבור WF-5390/5890', dealer:318, status:'request', mpn:'C13T11D140' },
  { id:'con2', brand:'Epson', name:'דיו ציאן 5K', spec:'עבור WF-5390/5890', dealer:318, status:'request', mpn:'C13T11D240' },
  { id:'con3', brand:'Epson', name:'דיו מגנטה 5K', spec:'עבור WF-5390/5890', dealer:318, status:'request', mpn:'C13T11D340' },
  { id:'con4', brand:'Epson', name:'דיו צהוב 5K', spec:'עבור WF-5390/5890', dealer:318, status:'request', mpn:'C13T11D440' },
  { id:'con5', brand:'Epson', name:'דיו שחור XXL', spec:'עבור WF-5390/5890', dealer:280, status:'request', mpn:'C13T11E140' },
  { id:'con6', brand:'Epson', name:'מגירת נייר 500 דפים', spec:'עבור WF-58xx/53xx', dealer:589, status:'request', mpn:'C12C93790' },
];

/* ── Map a raw catalog item to a storefront product ────────────── */
function _toProduct(it, category) {
  return {
    id: it.id,
    brand: it.brand,
    name: it.name,
    specs: it.spec,
    price: it.dealer,
    category: category,
    status: it.status || "request",
    mpn: it.mpn || it.code || "",
    bundle: it.bundle || "",
    badge: it.hot ? "מומלץ" : (it.status === "new" ? "חדש" : ""),
    // A photo at assets/products/{id}.jpg is used if present; otherwise the
    // onerror handler falls back to the clean category graphic.
    image: "assets/products/" + it.id + ".jpg",
  };
}

const _CATALOG = [
  ["מחשבים ניידים", _laptops],
  ["מחשבים נייחים", _desktops],
  ["מחשבי גיימינג", _gaming],
  ["כרטיסי מסך", _gpuItems],
  ["רכיבי מחשב", _components],
  ["סורקים", [].concat(_epsonScanners, _brotherScanners)],
  ["מדפסות", _workforce],
  ["מדפסות תוויות", _colorLabelPrinters],
  ["קופות ו-POS", _pos],
  ["מקרנים", _projectors],
  ["דיו ומתכלים", [].concat(_colorLabelInk, _consumables)],
];

const _PRODUCTS = [];
_CATALOG.forEach(function (pair) {
  pair[1].forEach(function (it) { _PRODUCTS.push(_toProduct(it, pair[0])); });
});

/* ── SITE DATA ─────────────────────────────────────────────────── */
window.SITE_DATA = {
  categories: [
    "כל המוצרים",
    "מחשבים ניידים",
    "מחשבים נייחים",
    "מחשבי גיימינג",
    "כרטיסי מסך",
    "רכיבי מחשב",
    "סורקים",
    "מדפסות",
    "מדפסות תוויות",
    "קופות ו-POS",
    "מקרנים",
    "דיו ומתכלים",
  ],

  heroSlides: [
    {
      image: "assets/banners/dell-latitude.png",
      fallbackImage: "assets/banners/asus-expertbook.png",
      alt: "DELL Latitude — הבחירה המקצועית לעסקים",
      link: "products.html?brand=Dell",
    },
    {
      image: "assets/banners/apple-macbook.png",
      fallbackImage: "assets/banners/asus-expertbook.png",
      alt: "Apple MacBook Air M3 — הבחירה המקצועית לעסקים",
      link: "products.html",
    },
  ],

  // Featured spots under the hero (must reference real product ids)
  featured: [
    { tag: "הנמכר ביותר", productId: "d3" },
    { tag: "מומלץ לעסקים", productId: "l1" },
    { tag: "חדש בקטלוג", productId: "g1" },
  ],

  // Brand logos row
  brands: ["HP", "Dell", "Lenovo", "Epson"],

  // Partners / testimonials
  partners: [
    {
      name: "פיצה האט",
      logo: "Pizza",
      image: "assets/partners/pizza.png",
      quote:
        "אנחנו עובדים עם רועי למעלה מ-10 שנים. הוא תמיד שם בנעימות ובמהירות ובמענה לכל בקשה שלנו.",
      person: "שמעון בכר, סמנכ\"ל IT",
    },
    {
      name: "דרך היין",
      logo: "Wine",
      image: "assets/partners/wine.png",
      quote:
        "שירות אישי ומקצועי לאורך כל הדרך. ליווי מלא מהאפיון ועד ההתקנה בכל הסניפים.",
      person: "שמעון בכר, סמנכ\"ל IT",
    },
    {
      name: "החברה למתנ\"סים",
      logo: "Community",
      image: "assets/partners/community.jpg",
      quote:
        "פתרונות מחשוב לארגון גדול ופרוס — מהירות תגובה וזמינות שעושות את ההבדל.",
      person: "שמעון בכר, סמנכ\"ל IT",
    },
    {
      name: "ePost",
      logo: "Post",
      image: "assets/partners/post.png",
      quote:
        "אמינות מלאה, מחירים הוגנים ושירות שלא מאכזב. שותפים אמיתיים לעסק.",
      person: "שמעון בכר, סמנכ\"ל IT",
    },
  ],

  // Full product catalog (imported + mapped above)
  products: _PRODUCTS,
};

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
  else if (/מסך|gpu|כרטיס/.test(c)) type = "gpu";
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
