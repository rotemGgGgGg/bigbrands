// Access control for Edge Lab.
// - No EDGE_LAB_PASSWORD: the app only listens on 127.0.0.1 and needs no login (your own computer).
// - With EDGE_LAB_PASSWORD: every API call needs a session cookie from /api/login. Required before the server
//   may listen on another interface or be reached through Tailscale or a reverse proxy.
import crypto from "node:crypto";

const COOKIE = "edge_session";
const TTL = 30 * 24 * 3600 * 1000;
const sha = (s) => crypto.createHash("sha256").update(String(s)).digest();

export class Auth {
  constructor(store, password) {
    this.store = store;
    this.enabled = !!password;
    this.hash = password ? sha(password) : null;
    this.attempts = new Map();                      // ip -> [timestamps of failed logins]
  }

  /** Session id from the cookie header, if it is a live session. */
  session(req) {
    if (!this.enabled) return { local: true };
    const raw = (req.headers.cookie || "").split(";").map((c) => c.trim().split("=")).find(([k]) => k === COOKIE)?.[1];
    if (!raw) return null;
    const key = sha(raw).toString("hex"), now = Date.now();
    const s = this.store.read("sessions", {})[key];
    return s && s.expires > now ? s : null;
  }

  /** Throttle: 5 failed attempts per 15 minutes per address. */
  blocked(ip) {
    const now = Date.now(), list = (this.attempts.get(ip) || []).filter((t) => now - t < 15 * 60 * 1000);
    this.attempts.set(ip, list);
    return list.length >= 5;
  }

  login(req, res, password, secure) {
    const ip = req.socket.remoteAddress || "?";
    if (this.blocked(ip)) return { ok: false, code: 429, error: "Too many attempts. Wait 15 minutes." };
    const ok = this.enabled && crypto.timingSafeEqual(sha(password || ""), this.hash);
    if (!ok) { this.attempts.get(ip).push(Date.now()); return { ok: false, code: 401, error: "Wrong password." }; }
    const token = crypto.randomBytes(32).toString("base64url"), key = sha(token).toString("hex");
    this.store.update("sessions", {}, (all) => {
      const now = Date.now();
      for (const [k, v] of Object.entries(all)) if (v.expires < now) delete all[k];
      all[key] = { created: new Date().toISOString(), expires: now + TTL, agent: String(req.headers["user-agent"] || "").slice(0, 120) };
      return all;
    });
    res.setHeader("set-cookie", `${COOKIE}=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=${TTL / 1000}${secure ? "; Secure" : ""}`);
    return { ok: true };
  }

  logout(req, res) {
    const raw = (req.headers.cookie || "").split(";").map((c) => c.trim().split("=")).find(([k]) => k === COOKIE)?.[1];
    if (raw) { const key = sha(raw).toString("hex"); this.store.update("sessions", {}, (all) => { delete all[key]; return all; }); }
    res.setHeader("set-cookie", `${COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0`);
  }

  /** Ends every session (e.g. after a lost phone). */
  logoutAll() { this.store.write("sessions", {}); }
}
