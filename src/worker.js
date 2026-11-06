import { searchPrices } from "./pricing.js";

const COOKIE = "bb_admin";
const SESSION_DAYS = 7;
const enc = new TextEncoder();

async function hmac(secret, data) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(data));
  return btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/[+/=]/g, (c) => ({ "+": "-", "/": "_", "=": "" }[c]));
}

// Compare via HMAC digests so the comparison time doesn't leak the password.
async function safeEqual(a, b, secret) {
  const [x, y] = await Promise.all([hmac(secret, "cmp:" + a), hmac(secret, "cmp:" + b)]);
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.min(x.length, y.length); i++) diff |= x.charCodeAt(i) ^ y.charCodeAt(i);
  return diff === 0;
}

const sessionSecret = (env) => env.ADMIN_SESSION_SECRET || "s:" + env.ADMIN_PASSWORD;

async function makeSession(env) {
  const exp = Date.now() + SESSION_DAYS * 864e5;
  return `${exp}.${await hmac(sessionSecret(env), "session:" + exp)}`;
}

async function isAuthed(request, env) {
  if (!env.ADMIN_PASSWORD) return false;
  const m = (request.headers.get("Cookie") || "").match(new RegExp(`(?:^|; )${COOKIE}=([^;]+)`));
  if (!m) return false;
  const [exp, sig] = m[1].split(".");
  if (!exp || !sig || Number(exp) < Date.now()) return false;
  return safeEqual(sig, await hmac(sessionSecret(env), "session:" + exp), sessionSecret(env));
}

const failures = new Map();
function tooManyAttempts(ip) {
  const f = failures.get(ip);
  return f && f.count >= 5 && Date.now() - f.at < 15 * 60e3;
}
function recordFailure(ip) {
  const f = failures.get(ip);
  failures.set(ip, f && Date.now() - f.at < 15 * 60e3 ? { count: f.count + 1, at: f.at } : { count: 1, at: Date.now() });
}

const SECURITY_HEADERS = {
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Cache-Control": "no-store",
  "X-Robots-Tag": "noindex, nofollow",
};
function withSecurity(res) {
  const r = new Response(res.body, res);
  for (const [k, v] of Object.entries(SECURITY_HEADERS)) r.headers.set(k, v);
  return r;
}

function loginPage(error = "") {
  return withSecurity(new Response(`<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>כניסה — BIG BRANDS</title><style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;padding:20px;font-family:system-ui,"Segoe UI",Arial,sans-serif;color:#1d2433;
background:radial-gradient(1200px 700px at 20% 10%,#ffffff 0%,transparent 60%),radial-gradient(900px 600px at 90% 90%,#cfd8e6 0%,transparent 60%),linear-gradient(135deg,#e9edf3,#d6dce6)}
.card{width:min(380px,100%);padding:30px 26px;border-radius:28px;background:rgba(255,255,255,.42);backdrop-filter:blur(26px) saturate(160%);-webkit-backdrop-filter:blur(26px) saturate(160%);
border:1px solid rgba(255,255,255,.7);box-shadow:0 30px 70px rgba(40,55,85,.18),inset 0 1px 0 rgba(255,255,255,.9)}
h1{margin:0 0 4px;font-size:22px}p{margin:0 0 22px;color:#5b6577;font-size:14px}
input{width:100%;padding:14px 16px;font-size:16px;border-radius:16px;border:1px solid rgba(255,255,255,.8);background:rgba(255,255,255,.6);outline:none}
input:focus{box-shadow:0 0 0 4px rgba(64,110,200,.18)}
button{width:100%;margin-top:12px;padding:14px;font-size:16px;font-weight:700;border:0;border-radius:16px;color:#fff;background:linear-gradient(135deg,#3b6fd8,#5c8ef0);cursor:pointer}
.err{color:#b42318;font-size:14px;margin:12px 0 0}</style></head><body>
<form class="card" method="post" action="/admin/login"><h1>BIG BRANDS · ניהול</h1><p>אזור מוגן. הזן סיסמה כדי להמשיך.</p>
<input type="password" name="password" placeholder="סיסמה" autocomplete="current-password" required autofocus>
<button>כניסה</button>${error ? `<p class="err">${error}</p>` : ""}</form></body></html>`,
    { status: error ? 401 : 200, headers: { "Content-Type": "text/html; charset=utf-8" } }));
}

const json = (data, status = 200) => withSecurity(new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8" } }));

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const isAdmin = path === "/admin" || path.startsWith("/admin/") || path.startsWith("/admin.") || path.startsWith("/api/") || path === "/js/admin.js";
    if (!isAdmin) return env.ASSETS.fetch(request);

    if (path === "/admin/login" && request.method === "POST") {
      if (!env.ADMIN_PASSWORD) return loginPage("הכניסה עדיין לא הוגדרה (חסר ADMIN_PASSWORD).");
      const ip = request.headers.get("CF-Connecting-IP") || "?";
      if (tooManyAttempts(ip)) return loginPage("יותר מדי ניסיונות. נסה שוב בעוד 15 דקות.");
      const form = await request.formData();
      if (!(await safeEqual(String(form.get("password") || ""), env.ADMIN_PASSWORD, sessionSecret(env)))) {
        recordFailure(ip);
        return loginPage("סיסמה שגויה.");
      }
      failures.delete(ip);
      return withSecurity(new Response(null, {
        status: 303,
        headers: {
          Location: "/admin/",
          "Set-Cookie": `${COOKIE}=${await makeSession(env)}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${SESSION_DAYS * 86400}`,
        },
      }));
    }

    if (path === "/admin/logout") {
      return withSecurity(new Response(null, { status: 303, headers: { Location: "/admin/", "Set-Cookie": `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0` } }));
    }

    if (!(await isAuthed(request, env))) {
      return path.startsWith("/api/") ? json({ error: "לא מחובר" }, 401) : loginPage();
    }

    if (path === "/api/prices") {
      const q = (url.searchParams.get("q") || "").trim().slice(0, 120);
      if (!q) return json({ error: "חסרה שאילתה" }, 400);
      const sources = (url.searchParams.get("sources") || "zap").split(",").slice(0, 6);
      try { return json(await searchPrices(q, sources, env)); }
      catch (e) { return json({ error: e.message }, 500); }
    }
    if (path.startsWith("/api/")) return json({ error: "לא נמצא" }, 404);

    if (path === "/admin") return Response.redirect(url.origin + "/admin/", 301);
    return withSecurity(await env.ASSETS.fetch(request));
  },
};
