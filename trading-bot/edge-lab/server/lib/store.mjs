// Tiny JSON-file store for app state (conversations, experiments, events, settings). Atomic writes.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

export class Store {
  constructor(dir) { this.dir = dir; fs.mkdirSync(dir, { recursive: true }); this.mem = {}; }

  #file(name) { return path.join(this.dir, `${name}.json`); }

  read(name, fallback) {
    if (name in this.mem) return this.mem[name];
    const f = this.#file(name);
    let v = fallback;
    try { if (fs.existsSync(f)) v = JSON.parse(fs.readFileSync(f, "utf8")); } catch (e) { console.error(`store: could not read ${f}: ${e.message}`); }
    return (this.mem[name] = v);
  }

  write(name, value) {
    this.mem[name] = value;
    const f = this.#file(name), tmp = `${f}.${process.pid}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(value, null, 1));
    fs.renameSync(tmp, f);
    return value;
  }

  update(name, fallback, fn) { const v = fn(structuredClone(this.read(name, fallback))); return this.write(name, v); }

  log(type, title, detail = {}) {
    const ev = { id: id("ev"), at: new Date().toISOString(), type, title, ...detail };
    this.update("events", [], (a) => { a.unshift(ev); return a.slice(0, 2000); });
    return ev;
  }
}

export const id = (prefix) => `${prefix}_${crypto.randomBytes(5).toString("hex")}`;
