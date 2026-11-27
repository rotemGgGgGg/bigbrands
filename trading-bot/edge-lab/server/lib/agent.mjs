// Research agent bridge: runs the Claude Code CLI in headless mode (`claude -p --output-format stream-json`)
// inside the research workspace, with an explicit tool allow-list per permission level and
// `--permission-mode dontAsk`, so anything outside the allow-list is refused rather than prompted.
// The browser never sends commands: it sends a message, the server builds the CLI call.
import { spawn, execFile, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const WIN = process.platform === "win32";
// On Windows Claude Code runs shell commands through its PowerShell tool, so every rule exists for both shells.
const both = (cmds) => cmds.flatMap((c) => [`Bash(${c})`, `PowerShell(${c})`]);
const PY = both(["python3 *", "/usr/bin/python3 *", "python *", "py *"]);
const READ_CMDS = [...both(["cd *", "ls *", "dir *", "cat *", "head *", "tail *", "git log *", "git diff *", "git status *"]),
  ...["Set-Location *", "Get-ChildItem *", "Get-Content *", "Select-Object *", "Select-String *", "Measure-Object *", "Test-Path *"].map((c) => `PowerShell(${c})`)];

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
    description: "Also edits and creates files and runs any shell command in the workspace (on Windows the PowerShell tool only obeys a whole-tool rule, so Build allows the whole shell).",
    tools: ["Read", "Glob", "Grep", ...PY, ...READ_CMDS, "Edit", "Write", ...(process.platform === "win32" ? ["PowerShell", "Bash"] : [])],
  },
};

export const MODELS = [
  { id: "", label: "Claude Code default", note: "Fable on some plans: needs credits" },
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
Be concise. Lead with the result.${WIN ? " This machine runs Windows; your shell is Git Bash. Call Python as `python`; your working directory is already the research folder, so run scripts with a relative forward-slash path (python timelinks/theory.py), one command per call, no cd." : ""}
Raw market data (1-minute bars) may be missing on this machine: many scripts point to a data folder from an earlier cloud session. Before a long run, check the inputs exist; if they do not, say exactly which files are missing instead of guessing.`;

/** Extra instructions for chat modes. */
export const MODES = {
  rotem: "Answer the way Rotem likes: short, straight to the point, no warm-up, explain clearly in simple words, Hebrew unless the question is in English. Lead with the result or the uncomfortable truth; use a small table when there are numbers.",
  usage: "Usage-saver mode: minimise tokens and tool calls. Read only the lines you need (grep, head, small ranges), never dump large files or long outputs, reuse what you already know from this conversation, batch work into one script run instead of many, skip exploration that is not needed for the answer, and keep the reply short.",
};

/**
 * Finds how to start the CLI without a shell. On Windows npm installs `claude.cmd`, which Node cannot spawn directly
 * (and must not be run through a shell with our arguments), so we read the shim and start its real target.
 */
/** bash.exe from Git for Windows, or null (non-Windows, or Git not found). Override with EDGE_LAB_GIT_BASH. */
export function findGitBash() {
  if (process.platform !== "win32") return null;
  const tries = [process.env.EDGE_LAB_GIT_BASH, process.env.CLAUDE_CODE_GIT_BASH_PATH,
    "C:\\Program Files\\Git\\bin\\bash.exe", "C:\\Program Files (x86)\\Git\\bin\\bash.exe",
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, "Programs", "Git", "bin", "bash.exe")];
  try {
    for (const g of execFileSync("where", ["git"], { encoding: "utf8", windowsHide: true }).split(/\r?\n/).filter(Boolean))
      tries.push(path.join(path.dirname(g), "..", "bin", "bash.exe"));
  } catch { /* git not on PATH */ }
  return tries.find((p) => p && fs.existsSync(p)) || null;
}

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
  run({ prompt, sessionId, permission = "analyze", model = "", billing = { mode: "subscription" }, extraSystem = "", onEvent }) {
    const perm = PERMISSIONS[permission] || PERMISSIONS.read;
    const args = ["-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
      "--permission-mode", "dontAsk", "--append-system-prompt", SYSTEM(this.workspace) + (extraSystem ? `\n${extraSystem}` : "")];
    if (model) args.push("--model", model);
    if (sessionId) args.push("--resume", sessionId);
    // Billing: "subscription" strips any API key so the CLI uses your Claude sign-in; "api" passes the server's key
    // (never the browser's) and caps the spend of each run.
    const env = { ...process.env };
    delete env.ANTHROPIC_API_KEY; delete env.EDGE_LAB_API_KEY;
    // Windows: Claude Code's PowerShell tool refuses commands in this non-interactive mode even under matching rules,
    // so switch the agent to Git Bash (ships with Git for Windows), where the python/cd rules behave.
    const gitBash = findGitBash();
    if (gitBash) { env.CLAUDE_CODE_USE_POWERSHELL_TOOL = "0"; env.CLAUDE_CODE_GIT_BASH_PATH = gitBash; }
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
        case "rate_limit_event":
          if (o.rate_limit_info) emit({ type: "limits", info: o.rate_limit_info });
          break;
        case "result":
          resultSeen = true;
          emit({
            type: "result", ok: !o.is_error, text: o.result ?? finalText, costUsd: o.total_cost_usd, durationMs: o.duration_ms, turns: o.num_turns,
            sessionId: o.session_id, error: o.is_error ? (o.api_error || o.terminal_reason || o.result || "The agent stopped with an error.") : null,
            denied: (o.permission_denials || []).map((d) => d.tool_name + (d.tool_input?.command ? `: ${String(d.tool_input.command).slice(0, 120)}` : "")),
            usage: summariseUsage(o),
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

/** Tokens of the last turn and the model's context window, from the CLI result. */
function summariseUsage(o) {
  const u = o.usage || {}, mu = Object.entries(o.modelUsage || {})[0];
  const context = (u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0);
  return { model: mu?.[0] || null, contextTokens: context, outputTokens: u.output_tokens || 0, contextWindow: mu?.[1]?.contextWindow || null };
}
