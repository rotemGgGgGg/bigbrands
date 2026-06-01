/*
  DEFAULT SITE CONTENT (seed data)
  --------------------------------
  This is the "simple, replaceable" data layer. The temporary admin panel
  reads/writes a copy of this in the browser (localStorage). When you build
  your real custom admin later, only this file + js/store.js need to change —
  the storefront (index.html / main.js) stays the same.

  To change products by hand, just edit the PRODUCTS array below.
  Prices are in ILS (₪). Images use a built-in placeholder generator, so you
  can leave `image` empty and a clean device graphic is drawn automatically.
*/

window.SITE_DATA = {
  // Top category navigation (right-to-left order as written)
  categories: [
    "כל המוצרים",
    "ניידים",
    "נייחים",
    "מסכים",
    "ניידים לעסקים",
    "מוצרים מחודשים",
    "מקרנים",
    "אוזניות",
    "סלולר",
  ],

  /* Sliding hero ads. Two kinds of slide:
     1) A pre-made banner image  -> set `image` to the file path (full-bleed).
     2) A designed slide          -> set eyebrow/title/subtitle/cta/accent.
     To swap the first ad to your Dell banner: drop the file at
     assets/banners/dell-latitude.jpg and set image to that path. */
  heroSlides: [
    {
      image: "assets/banners/dell-latitude.jpg", // your Dell banner — drop the file here
      fallbackImage: "assets/banners/asus-expertbook.png", // shown until the Dell file exists
      alt: "באנר ראשי",
      link: "products.html?brand=Dell",
    },
    {
      eyebrow: "Apple · MacBook Air M3",
      title: "קל. מהיר. אלגנטי.",
      subtitle: "הביצועים של שבב M3, במשקל נוצה",
      cta: "גלו עכשיו",
      accent: "#111418",
      link: "products.html?brand=Apple",
    },
    {
      eyebrow: "אוזניות Sony / מקצועיות",
      title: "שקט מושלם, סאונד מדויק",
      subtitle: "בידוד רעשים אקטיבי לעבודה ולבית",
      cta: "להאזנה",
      accent: "#e10a17",
      link: "products.html?category=אוזניות",
    },
  ],

  // The three featured spots under the hero
  featured: [
    { tag: "הנמכר ביותר היום", productId: "p-lenovo-e14-1" },
    { tag: "הנמכר ביותר השבוע", productId: "p-dell-16plus" },
    { tag: "מומלץ על ידי הגולשים", productId: "p-apple-air-m3" },
  ],

  // Brand logos row
  brands: ["HP", "Dell", "Apple", "Lenovo"],

  // Partners / testimonials ("working with the big businesses")
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

  // Product catalog (seed). Edit freely or manage via the temporary admin.
  products: [
    {
      id: "p-lenovo-e14-1",
      brand: "Lenovo",
      name: "מחשב נייד Lenovo ThinkPad E14 Gen 7 | 21SX005AIV",
      specs: "Ultra 7 255H | 16G | 1T | Arc 140T | W11 Pro",
      price: 4990,
      category: "ניידים לעסקים",
      badge: "נייד חדש",
      image: "",
    },
    {
      id: "p-lenovo-e14-2",
      brand: "Lenovo",
      name: "מחשב נייד Lenovo ThinkPad E14 Gen 7 | 21SX0059IV",
      specs: "Ultra 5 225U | 8G | 256G | Intel Graphics | W11 Pro",
      price: 3780,
      category: "ניידים לעסקים",
      badge: "",
      image: "",
    },
    {
      id: "p-lenovo-e14-3",
      brand: "Lenovo",
      name: "מחשב נייד Lenovo ThinkPad E14 Gen 7 | 21SX0058IV",
      specs: "Ultra 5 225U | 8G | 256G",
      price: 3180,
      category: "ניידים לעסקים",
      badge: "",
      image: "",
    },
    {
      id: "p-lenovo-e14-4",
      brand: "Lenovo",
      name: "מחשב נייד Lenovo ThinkPad E14 Gen 7 | 21SX0056IV",
      specs: "Ultra 7 255H | 16G | 1T | Arc 140T",
      price: 4490,
      category: "ניידים לעסקים",
      badge: "",
      image: "",
    },
    {
      id: "p-lenovo-e14-5",
      brand: "Lenovo",
      name: "מחשב נייד Lenovo ThinkPad E14 Gen 7 | Ultra 7 255H",
      specs: "16G | 512G | Arc 140T",
      price: 4380,
      category: "ניידים לעסקים",
      badge: "",
      image: "",
    },
    {
      id: "p-dell-15",
      brand: "Dell",
      name: "Dell 15 DC15250",
      specs: "Core 7 | 16G | 512G SSD | מסך 15.6\"",
      price: 3690,
      category: "ניידים",
      badge: "נייד חדש המומלץ לעסק",
      image: "",
    },
    {
      id: "p-dell-16plus",
      brand: "Dell",
      name: "Dell 16 Plus DB16250",
      specs: "Core Ultra 7 | 16G | 1T SSD | מסך 16\"",
      price: 4790,
      category: "ניידים",
      badge: "נייד חדש המומלץ לעסק",
      image: "",
    },
    {
      id: "p-dell-pro",
      brand: "Dell",
      name: "Dell Pro Premium MA14250",
      specs: "Core Ultra 7 | 32G | 1T SSD | מסך 14\"",
      price: 6290,
      category: "ניידים לעסקים",
      badge: "נייד חדש המומלץ לעסק",
      image: "",
    },
    {
      id: "p-apple-air-m3",
      brand: "Apple",
      name: "Apple MacBook Air 13\" M3",
      specs: "שבב M3 | 8 ליבות | 16G | 256G SSD",
      price: 4990,
      category: "ניידים",
      badge: "מומלץ",
      image: "",
    },
    {
      id: "p-hp-elitebook",
      brand: "HP",
      name: "HP EliteBook 640 G11",
      specs: "Core Ultra 5 | 16G | 512G SSD | W11 Pro",
      price: 4290,
      category: "ניידים לעסקים",
      badge: "",
      image: "",
    },
    {
      id: "p-asus-expertbook",
      brand: "ASUS",
      name: "ASUS ExpertBook B1 B1403",
      specs: "Core i7 | 16G | 512G SSD | W11 Pro",
      price: 3990,
      category: "ניידים לעסקים",
      badge: "מבצע",
      image: "",
    },
    {
      id: "p-sony-headphones",
      brand: "Sony",
      name: "אוזניות Sony WH-1000XM5",
      specs: "בידוד רעשים אקטיבי | Bluetooth | 30 שעות",
      price: 1290,
      category: "אוזניות",
      badge: "",
      image: "",
    },
  ],
};
