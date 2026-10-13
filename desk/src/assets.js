// The two small files that make the page installable as an app. On a phone,
// "Add to Home Screen" then opens it full screen with its own icon.
export const MANIFEST = JSON.stringify({
  name: "Tape",
  short_name: "Tape",
  start_url: "/",
  display: "standalone",
  background_color: "#f6f3ec",
  theme_color: "#f6f3ec",
  icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
});

export const ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#f6f3ec"/>
<path d="M17 18h30v7H35.5v23h-7V25H17z" fill="#252a3a"/>
<g fill="#2f8a62"><rect x="17" y="51" width="3" height="5"/><rect x="25" y="51" width="3" height="5"/><rect x="37" y="51" width="3" height="5"/></g>
<g fill="#c4502f"><rect x="21" y="51" width="3" height="5"/><rect x="31" y="51" width="3" height="5"/><rect x="43" y="51" width="3" height="5"/></g>
</svg>`;
