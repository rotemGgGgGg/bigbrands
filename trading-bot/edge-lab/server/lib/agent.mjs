// Research agent bridge: runs the Claude Code CLI in headless mode (`claude -p --output-format stream-json`)
// inside the research workspace, with an explicit tool allow-list per permission level and
// `--permission-mode dontAsk`, so anything outside the allow-list is refused rather than prompted.
// The browser never sends commands: it sends a message, the server builds the CLI call.
import { spawn, execFile, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const WIN = process.platform === "win32";
const PY = ["Bash(python3 *)", "Bash(/usr/bin/python3 *)", "Bash(python *)", "Bash(py *)"];
const READ_CMDS = ["Bash(ls *)", "Bash(dir *)", "Bash(git log *)", "Bash(git diff *)", "Bash(git status *)"];

export const PERMISSIONS = {
  read: {
    label: "Read only",
    description: "Reads and searches files in the research workspace. Runs nothing, changes nothing.",
    tools: ["Read", "Glob", "Grep"],
  },
  analyze: {
    label: "Analyze",
    description: "Also runs Python research scripts and read-only git commands. Python can do anything a script can, inside your machine.",
    tools: ["Read", "Glob", "Grep", ...PY, ...READ_CMDS],
  },
  build: {
    label: "Build",
    description: "Also edits and creates files in the workspace, so it can write new strategy variations and tests.",
    tools: ["Read", "Glob", "Grep", ...PY, ...READ_CMDS, "Edit", "Write"],
  },
};

export const MODELS = [
  { id: "", label: "Claude Code default" },
  { id: "opus", label: "Opus" },
  { id: "sonnet", label: "Sonnet" },
  { id: "haiku", label: "Haiku" },
];

const SYSTEM = (ws) => `You are the research agent inside Edge Lab, a personal quant research workspace for NQ (Nasdaq futures) and JPY-cross strategies.
Workspace: ${ws}. Key places: lab/data.json (strategy registry, built by lab/build.py), lab/trades.json (per-trade R series, built by lab/export_trades.py),
allo/ (AVP, convex RDM, meta-labelling), creative/ (RDM, theory factories), gotobi/, spmodel/ (SP model v8), layers/ (13M multi-timeframe factory), */RESULTS.md (findings).
Rules of this research: choose parameters on 2012-19 only and judge once on 2020-26; include costs (1 NQ point round trip unless stated);
compare against a random twin (shifted clocks, shuffled days, random direction, shifted zones) and report p; never relax a gate after looking.
Never invent numbers: every figure you report must come from code you ran or a file you read. If you could not run something, say so.
When you report a test result, give a short table (trades/yr, win %, avg R, 2012-19 and 2020-26 avg R with t, positive years, random p), then end with
one fenced json block: {"trades_per_year":..,"win_rate":..,"avg_r":..,"is_avg_r":..,"oos_avg_r":..,"oos_t":..,"positive_years":"x/y","p_random":..,"verdict":"live|watch|dead"} using null for anything not measured.
Be concise. Lead with the result.${WIN ? " This machine runs Windows: call Python as `python`." : ""}`;

/**
 * Finds how to start the CLI without a shell. On Windows npm installs `claude.cmd`, which Node cannot spawn directly
 * (and must not be run through a shell with our arguments), so we read the shim and start its real target.
 */
export function resolveClaude(bin = process.env.CLAUDE_BIN || "claude") {
  if (!WIN) return { cmd: bin, pre: [] };
  let candidates = [];
  if (/[\\/]/.test(bin)) candidates = [bin];
  else { try { candidates = execFileSync("where.exe", [bin], { encoding: "utf8", timeout: 10000 }).split(/\r?\n/).filter(Boolean); } catch { return { cmd: bin, pre: [], missing: true }; } }
  const exe = candidates.find((c) => /\.exe$/i.test(c)); if (exe) return { cmd: exe, pre: [] };
  for (const c of candidates.filter((x) => /\.cmd$/i.test(x))) {
    const text = fs.readFileSync(c, "utf8"), dir = path.dirname(c);
    const targets = [...text.matchAll(/%~?dp0%?\\([^"%\r\n]+)/gi)].map((m) => path.join(dir, m[1].trim()));
    const t = targets.find((x) => /\.exe$/i.test(x) && fs.existsSync(x)) || targets.find((x) => /\.(c|m)?js$/i.test(x) && fs.existsSync(x));
    if (t) return /\.exe$/i.test(t) ? { cmd: t, pre: [] } : { cmd: process.execPath, pre: [t] };
  }
  return { cmd: candidates[0] || bin, pre: [] };
}

export class Agent {
  constructor({ workspace }) { this.workspace = workspace; this.status = null; this.launch = resolveClaude(); }

  /** Detects the CLI. Does not prove the account can run a model; `test()` does. */
  detect() {
    return new Promise((resolve) => {
      this.launch = resolveClaude();
      execFile(this.launch.cmd, [...this.launch.pre, "--version"], { timeout: 20000, windowsHide: true }, (err, stdout) => {
        this.status = err ? { available: false, error: err.code === "ENOENT" || this.launch.missing ? "Claude Code CLI not found. Install it (npm install -g @anthropic-ai/claude-code) or set CLAUDE_BIN." : err.message }
          : { available: true, version: stdout.trim() };
        resolve(this.status);
      });
    });
  }

  /**
   * Starts one headless run. Emits normalised events through onEvent and resolves when the process ends.
   * Returns { cancel }.
   */
  run({ prompt, sessionId, permission = "analyze", model = "", billing = { mode: "subscription" }, onEvent }) {
    const perm = PERMISSIONS[permission] || PERMISSIONS.read;
    const args = ["-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
      "--permission-mode", "dontAsk", "--append-system-prompt", SYSTEM(this.workspace)];
    if (model) args.push("--model", model);
    if (sessionId) args.push("--resume", sessionId);
    // Billing: "subscription" strips any API key so the CLI uses your Claude sign-in; "api" passes the server's key
    // (never the browser's) and caps the spend of each run.
    const env = { ...process.env };
    delete env.ANTHROPIC_API_KEY; delete env.EDGE_LAB_API_KEY;
    if (billing.mode === "api") {
      env.ANTHROPIC_API_KEY = billing.apiKey;
      if (billing.maxBudgetUsd) args.push("--max-budget-usd", String(billing.maxBudgetUsd));
    }
    args.push("--allowedTools", ...perm.tools);
    const child = spawn(this.launch.cmd, [...this.launch.pre, ...args], { cwd: this.workspace, env, stdio: ["pipe", "pipe", "pipe"], windowsHide: true });
    child.stdin.end(prompt);

    let buf = "", stderr = "", sawDelta = false, finalText = "", resultSeen = false, cancelled = false;
    const tools = new Map();
    const emit = (e) => onEvent?.(e);
    emit({ type: "phase", phase: "starting", label: "Starting agent" });

    const handle = (o) => {
      switch (o.type) {
        case "system":
          if (o.subtype === "init") emit({ type: "init", sessionId: o.session_id, model: o.model, permissionMode: o.permissionMode });
          break;
        case "stream_event": {
          const ev = o.event || {};
          if (ev.type === "content_block_start" && ev.content_block?.type === "text") {
            emit({ type: "phase", phase: "writing", label: "Writing" });
            if (finalText && !finalText.endsWith("\n")) { finalText += "\n\n"; emit({ type: "delta", text: "\n\n" }); }
          }
          if (ev.type === "content_block_delta" && ev.delta?.type === "text_delta") { sawDelta = true; finalText += ev.delta.text; emit({ type: "delta", text: ev.delta.text }); }
          if (ev.type === "message_start") sawDelta = false;
          break;
        }
        case "assistant": {
          const content = o.message?.content || [];
          if (o.error || o.message?.model === "<synthetic>") {
            const msg = content.map((c) => c.text).filter(Boolean).join(" ") || o.error;
            emit({ type: "error", message: msg, code: o.error });
            break;
          }
          for (const c of content) {
            if (c.type === "tool_use") {
              const info = describeTool(c.name, c.input);
              tools.set(c.id, info);
              emit({ type: "tool", id: c.id, ...info });
              emit({ type: "phase", phase: info.phase, label: info.phaseLabel });
            } else if (c.type === "text" && !sawDelta && c.text) { finalText += c.text; emit({ type: "delta", text: c.text }); }
          }
          break;
        }
        case "user":
          for (const c of o.message?.content || []) {
            if (c.type === "tool_result") {
              const text = Array.isArray(c.content) ? c.content.map((x) => x.text || "").join("") : String(c.content ?? "");
              emit({ type: "tool_result", id: c.tool_use_id, ok: !c.is_error, preview: text.slice(0, 600) });
              emit({ type: "phase", phase: "thinking", label: "Analyzing results" });
            }
          }
          break;
        case "result":
          resultSeen = true;
          emit({
            type: "result", ok: !o.is_error, text: o.result ?? finalText, costUsd: o.total_cost_usd, durationMs: o.duration_ms, turns: o.num_turns,
            sessionId: o.session_id, error: o.is_error ? (o.api_error || o.terminal_reason || o.result || "The agent stopped with an error.") : null,
            denied: (o.permission_denials || []).map((d) => d.tool_name),
          });
          break;
      }
    };

    child.stdout.on("data", (chunk) => {
      buf += chunk;
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
        if (!line) continue;
        try { handle(JSON.parse(line)); } catch { /* non-JSON line from the CLI: ignore */ }
      }
    });
    child.stderr.on("data", (c) => { stderr += c; if (stderr.length > 20000) stderr = stderr.slice(-20000); });

    const done = new Promise((resolve) => {
      child.on("error", (err) => { emit({ type: "error", message: err.code === "ENOENT" ? "Claude Code CLI not found." : err.message }); });
      child.on("close", (code) => {
        if (cancelled) emit({ type: "cancelled" });
        else if (!resultSeen) emit({ type: "error", message: stderr.trim().split("\n").slice(-3).join(" ") || `Agent exited with code ${code}.` });
        emit({ type: "end", code });
        resolve();
      });
    });

    const timer = setTimeout(() => { cancelled = true; child.kill("SIGTERM"); }, 30 * 60 * 1000);
    done.then(() => clearTimeout(timer));
    return { done, cancel: () => { cancelled = true; child.kill("SIGTERM"); setTimeout(() => child.kill("SIGKILL"), 4000).unref(); } };
  }
}

/** Human-readable label and work phase for a tool call. */
function describeTool(name, input = {}) {
  const short = (p) => (p ? String(p).split("/").slice(-2).join("/") : "");
  if (name === "Read") return { name, summary: `Read ${short(input.file_path)}`, phase: "analyzing", phaseLabel: "Reading files" };
  if (name === "Grep") return { name, summary: `Search “${input.pattern}”`, phase: "analyzing", phaseLabel: "Searching the project" };
  if (name === "Glob") return { name, summary: `Find ${input.pattern}`, phase: "analyzing", phaseLabel: "Searching the project" };
  if (name === "Edit" || name === "Write") return { name, summary: `${name === "Edit" ? "Edit" : "Write"} ${short(input.file_path)}`, phase: "coding", phaseLabel: "Writing code" };
  if (name === "Bash") {
    const cmd = String(input.command || "");
    const running = /python/.test(cmd);
    return { name, summary: input.description || (running ? "Run a Python research script" : "Run a command"), command: cmd.slice(0, 400), phase: running ? "running" : "working", phaseLabel: running ? "Running research" : "Running a command" };
  }
  return { name, summary: name, phase: "working", phaseLabel: "Working" };
}
