/**
 * Web Push, done by hand with WebCrypto, so the desk needs no library.
 *
 * Each phone or browser that turns notifications on hands the desk a
 * subscription: an address at its push service plus two keys. A message is
 * encrypted for those keys (RFC 8291, aes128gcm) and signed with the desk's
 * own key (VAPID, RFC 8292), and the push service wakes the page's service
 * worker, which shows it. Subscriptions the push service no longer knows are
 * dropped the first time a send to them fails with 404 or 410.
 */
const enc = new TextEncoder();

const b64u = (buf) =>
  btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

function unb64u(s) {
  const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

function concat(...parts) {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let i = 0;
  for (const p of parts) { out.set(p, i); i += p.length; }
  return out;
}

async function hkdf(salt, ikm, info, length) {
  const key = await crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: "HKDF", hash: "SHA-256", salt, info }, key, length * 8));
}

/** The VAPID header: a short-lived token, signed with the desk's private key. */
async function vapid(env, endpoint) {
  const jwk = JSON.parse(env.VAPID_PRIVATE_JWK);
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  const head = b64u(enc.encode(JSON.stringify({ typ: "JWT", alg: "ES256" })));
  const body = b64u(enc.encode(JSON.stringify({
    aud: new URL(endpoint).origin,
    exp: Math.floor(Date.now() / 1000) + 12 * 3600,
    sub: env.VAPID_SUBJECT || "mailto:desk@example.com",
  })));
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, enc.encode(`${head}.${body}`));
  return `vapid t=${head}.${body}.${b64u(sig)}, k=${env.VAPID_PUBLIC}`;
}

/** The message body, encrypted so only that one browser can read it. */
async function encrypt(sub, payload) {
  const uaPublic = unb64u(sub.keys.p256dh);
  const auth = unb64u(sub.keys.auth);
  const local = await crypto.subtle.generateKey({ name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]);
  const asPublic = new Uint8Array(await crypto.subtle.exportKey("raw", local.publicKey));
  const peer = await crypto.subtle.importKey("raw", uaPublic, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const shared = new Uint8Array(await crypto.subtle.deriveBits({ name: "ECDH", public: peer }, local.privateKey, 256));

  const ikm = await hkdf(auth, shared, concat(enc.encode("WebPush: info\0"), uaPublic, asPublic), 32);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const cek = await hkdf(salt, ikm, enc.encode("Content-Encoding: aes128gcm\0"), 16);
  const nonce = await hkdf(salt, ikm, enc.encode("Content-Encoding: nonce\0"), 12);

  const key = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, ["encrypt"]);
  // One record, so the padding delimiter is 2 ("last record").
  const plain = concat(enc.encode(payload), new Uint8Array([2]));
  const sealed = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, key, plain));

  const rs = new Uint8Array([0, 0, 16, 0]); // 4096, big-endian
  return concat(salt, rs, new Uint8Array([asPublic.length]), asPublic, sealed);
}

export async function listSubs(env) {
  const row = await env.DB.prepare("SELECT v FROM meta WHERE k = 'push'").first();
  return row ? JSON.parse(row.v) : [];
}

async function saveSubs(env, subs) {
  await env.DB.prepare(
    "INSERT INTO meta (k, v, ts) VALUES ('push', ?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v, ts=excluded.ts",
  ).bind(JSON.stringify(subs), Math.floor(Date.now() / 1000)).run();
}

export async function subscribe(env, sub) {
  if (!sub || typeof sub.endpoint !== "string" || !sub.endpoint.startsWith("https://")
      || !sub.keys || !sub.keys.p256dh || !sub.keys.auth) return { error: "bad subscription" };
  const subs = (await listSubs(env)).filter((s) => s.endpoint !== sub.endpoint);
  subs.push({ endpoint: sub.endpoint, keys: { p256dh: sub.keys.p256dh, auth: sub.keys.auth }, at: Date.now() });
  await saveSubs(env, subs.slice(-10));
  return { ok: true, devices: Math.min(subs.length, 10) };
}

export async function unsubscribe(env, endpoint) {
  const subs = await listSubs(env);
  const kept = subs.filter((s) => s.endpoint !== endpoint);
  if (kept.length !== subs.length) await saveSubs(env, kept);
  return { ok: true, devices: kept.length };
}

/** Sends one notification to every device that asked for them. */
export async function notifyAll(env, msg) {
  if (!env.VAPID_PRIVATE_JWK || !env.VAPID_PUBLIC) return { sent: 0, reason: "no vapid keys" };
  const subs = await listSubs(env);
  if (!subs.length) return { sent: 0 };
  const payload = JSON.stringify(msg);
  const results = await Promise.all(subs.map(async (s) => {
    try {
      const r = await fetch(s.endpoint, {
        method: "POST",
        headers: {
          authorization: await vapid(env, s.endpoint),
          "content-encoding": "aes128gcm",
          "content-type": "application/octet-stream",
          ttl: "3600",
          urgency: "high",
        },
        body: await encrypt(s, payload),
      });
      return { endpoint: s.endpoint, status: r.status };
    } catch (e) {
      return { endpoint: s.endpoint, status: 0, error: String(e) };
    }
  }));
  const gone = results.filter((r) => r.status === 404 || r.status === 410).map((r) => r.endpoint);
  if (gone.length) await saveSubs(env, subs.filter((s) => !gone.includes(s.endpoint)));
  return { sent: results.filter((r) => r.status >= 200 && r.status < 300).length, results };
}

/** The service worker: shows what arrives, and opens the desk when tapped. */
export const SW = `
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("push", (e) => {
  let m = {};
  try { m = e.data ? e.data.json() : {}; } catch (_) { m = { title: "Tape", body: e.data && e.data.text() }; }
  e.waitUntil(self.registration.showNotification(m.title || "Tape", {
    body: m.body || "", tag: m.tag, renotify: true, icon: "/icon.svg", badge: "/icon.svg",
    data: { url: m.url || "/" },
  }));
});
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
    for (const c of list) { if ("focus" in c) { c.navigate(url).catch(() => {}); return c.focus(); } }
    return self.clients.openWindow(url);
  }));
});
`;
