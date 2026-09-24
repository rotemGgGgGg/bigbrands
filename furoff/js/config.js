/*
  FUROFF CONFIG — everything business-specific lives here.
  Checkout uses Shopify cart permalinks: https://<shop>/cart/<variantId>:<qty>?discount=<code>
  so no API token is needed in the frontend.
*/
window.FUROFF = {
  shop: "uhtscw-cx.myshopify.com",
  variantId: "55030438756691",

  // Bundle prices MUST match real discount codes in Shopify, or checkout shows a different total.
  bundles: [
    { qty: 1, price: 99, title: "FurOff אחד", note: "לבית" },
    { qty: 2, price: 178, compare: 198, code: "FUROFF2", tag: "הכי פופולרי", title: "זוג FurOff", note: "לבית + לרכב" },
    { qty: 3, price: 237, compare: 297, code: "FUROFF3", tag: "הכי משתלם", title: "שלישייה", note: "לבית, לרכב ולמתנה" },
  ],
  defaultBundle: 1,

  shippingText: "משלוח חינם עד הבית, אספקה תוך 2–3 שבועות.",

  // Demo video (mp4 in assets/). Leave empty and the section stays hidden.
  videoUrl: "",
  guaranteeDays: 30,

  // Texts to paste into Shopify → Settings → Policies live in furoff-policies/.
  policies: [
    ["מדיניות החזרות", "https://uhtscw-cx.myshopify.com/policies/refund-policy"],
    ["משלוחים", "https://uhtscw-cx.myshopify.com/policies/shipping-policy"],
    ["תקנון", "https://uhtscw-cx.myshopify.com/policies/terms-of-service"],
    ["מדיניות פרטיות", "https://uhtscw-cx.myshopify.com/policies/privacy-policy"],
  ],

  // Real reviews only. Leave empty and the section stays hidden.
  // { name: "דנה, תל אביב", dog: "גולדן רטריבר", text: "...", stars: 5, photo: "assets/..." }
  reviews: [],
};
