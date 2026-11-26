// Builds dist/: a static Edge Lab (no Node server, no agent) for Lovable, Netlify, Vercel or GitHub Pages.
// Usage: npm run build:static   → upload or import the dist/ folder.
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const LAB = path.resolve(process.env.RESEARCH_DIR || path.join(ROOT, "..", "research"), "lab");
const OUT = path.join(ROOT, "dist");

fs.rmSync(OUT, { recursive: true, force: true });
fs.cpSync(path.join(ROOT, "public"), OUT, { recursive: true });
fs.mkdirSync(path.join(OUT, "js", "engine"), { recursive: true });
for (const f of ["stats.mjs", "enrich.mjs", "montecarlo.mjs", "portfolio.mjs"]) fs.copyFileSync(path.join(ROOT, "server", "lib", f), path.join(OUT, "js", "engine", f));
fs.mkdirSync(path.join(OUT, "data"), { recursive: true });
for (const f of ["data.json", "trades.json"]) fs.copyFileSync(path.join(LAB, f), path.join(OUT, "data", f));

let commits = [];
try {
  const out = execFileSync("git", ["-C", ROOT, "log", "-n", "200", "--date=iso-strict", "--format=%H%x1f%ad%x1f%s", "--", path.join(LAB, "..")], { encoding: "utf8" });
  commits = out.trim().split("\n").filter(Boolean).map((l) => { const [h, at, s] = l.split("\x1f"); return { id: h.slice(0, 10), at, type: "commit", title: s }; });
} catch { /* no git: history shows app events only */ }
fs.writeFileSync(path.join(OUT, "data", "history.json"), JSON.stringify(commits));

const idx = path.join(OUT, "index.html");
fs.writeFileSync(idx, fs.readFileSync(idx, "utf8").replace('<html lang="en">', '<html lang="en" data-static="1">'));
fs.writeFileSync(path.join(OUT, "README.txt"), "Edge Lab, static build. Any static host serves this folder as-is (index.html at the root).\nThe research agent is not included: it runs only in the local app (npm start).\n");
const size = (d) => fs.readdirSync(d, { withFileTypes: true }).reduce((a, e) => a + (e.isDirectory() ? size(path.join(d, e.name)) : fs.statSync(path.join(d, e.name)).size), 0);
console.log(`dist/ ready · ${(size(OUT) / 1024).toFixed(0)} KB · ${commits.length} commits in history`);
