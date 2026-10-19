"""NQ opening-edge portfolio — live bot (OANDA NAS100_USD). Runs forever; all times New York (STRATEGY_NQ.md).
  09:00:05  Pre-Open Fade   — market order against an extreme 08:00→08:59 move, TP 0.5× / SL 1.0× the move   (exit 13:00)
  09:30:05  Opex short      — 3rd Friday only: market short, SL 0.4σ / TP 0.8σ                                  (exit 15:55)
  09:45:05  GapFB-NQ        — one resting stop entry (GTD 10:30), 2×ATR stop + 5×ATR trailing stop               (exit 15:55)
  13:00:00  close Pre-Fade leftovers · 15:55:00 close everything · 16:05:00 journal + daily Telegram summary
Usage:  python3 bot.py            run the schedule
        python3 bot.py --check    connect, print balance and what each strategy would do now (sends nothing)
        python3 bot.py --dry-run  full schedule, orders are logged instead of sent"""
from __future__ import annotations

import argparse, csv, json, logging, sys, time
from datetime import date, datetime
from pathlib import Path

import requests

from broker_oanda import Oanda
from strategy import NY, evaluate, opex, prefade

HERE = Path(__file__).resolve().parent
log = logging.getLogger("bot")


def load_config() -> dict:
    p = HERE / "config.json"
    if not p.exists():
        sys.exit("config.json missing — copy config.example.json to config.json and fill in your OANDA token + account id")
    return json.loads(p.read_text())


def at(d: date, hh: int, mm: int, ss: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, ss, tzinfo=NY)


class Bot:
    def __init__(self, cfg: dict, dry: bool):
        self.cfg, self.dry = cfg, dry
        self.br = Oanda(cfg["token"], cfg["account_id"], cfg.get("environment", "practice"), cfg.get("instrument", "NAS100_USD"))
        self.risk_pct = float(cfg.get("risk_pct", 1.0))
        self.enabled = cfg.get("strategies", {"gapfb": True, "prefade": True, "opex": True})
        self.state_path = HERE / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}

    # ---- helpers ----
    def save(self):
        self.state_path.write_text(json.dumps(self.state, indent=1))

    def say(self, msg: str):
        log.info(msg)
        tg = self.cfg.get("telegram", {})
        if tg.get("bot_token") and tg.get("chat_id"):
            try:
                requests.post(f"https://api.telegram.org/bot{tg['bot_token']}/sendMessage",
                              json={"chat_id": tg["chat_id"], "text": ("[DEMO] " if self.cfg.get("environment", "practice") == "practice" else "")
                                    + msg}, timeout=10)
            except Exception as e:
                log.warning("telegram failed: %s", e)

    def units(self, stop_distance: float) -> float:
        risk_usd = self.br.balance() * self.risk_pct / 100
        return self.br.units_for_risk(risk_usd, stop_distance)

    def conflict(self, side: int) -> bool:
        net = self.br.net_side()
        if net and net != side:
            self.say("skipped: an opposite position is already open (netting account)")
            return True
        return False

    def market(self, o):
        u = self.units(o.stop_distance)
        side = "LONG" if o.side == 1 else "SHORT"
        if u <= 0:
            self.say(f"{o.name}: size below broker minimum — skipped"); return
        if self.conflict(o.side): return
        self.say(f"{o.name.upper()} {side} {u} units | SL {o.stop_distance:.2f} pts TP {o.target_distance:.2f} pts | {o.info}")
        if not self.dry:
            self.br.market_bracket(o.name, o.side, u, o.stop_distance, o.target_distance)

    # ---- jobs ----
    def job_prefade(self, d: date):
        o, why = prefade(self.br.candles("M30", 2000), d)
        if o is None: log.info("prefade: %s", why); return
        self.market(o)

    def job_opex(self, d: date):
        o, why = opex(self.br.candles("M30", 2000), d)
        if o is None: log.info("opex: %s", why); return
        self.market(o)

    def job_gapfb(self, d: date):
        sig, why = evaluate(self.br.candles_m1(5000), d)
        if sig is None:
            self.say(f"GapFB: no trade today — {why}"); return
        u = self.units(sig.stop_distance)
        side = "LONG" if sig.side == 1 else "SHORT"
        if u <= 0:
            self.say("GapFB: size below broker minimum — skipped"); return
        if self.conflict(sig.side): return
        self.say(f"GapFB {side} stop-entry {sig.level:.2f} (until 10:30) | gap {sig.gap*100:+.2f}% score {sig.score} | "
                 f"stop {sig.stop_distance:.2f} trail {sig.trail_distance:.2f} pts | {u} units")
        if not self.dry:
            self.br.place_stop_entry(sig.side, u, sig.level, sig.stop_distance, sig.trail_distance, at(d, 10, 30))

    def job_close_prefade(self, d: date):
        if not self.dry:
            n = self.br.close_tagged("prefade")
            if n: self.say(f"13:00 closed {n} Pre-Fade trade(s)")

    def job_flatten(self, d: date):
        if self.dry: return
        n = self.br.cancel_pending(); r = self.br.close_position()
        if n or r: self.say(f"15:55 flat (cancelled {n} pending, {'closed position' if r else 'nothing open'})")

    def job_journal(self, d: date):
        path = HERE / "journal.csv"; new = not path.exists()
        rows = [t for t in self.br.closed_trades(30) if t.get("closeTime", "")[:10] == str(d)]
        with path.open("a", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(["date", "strategy", "units", "open_time", "entry", "close_time", "exit", "pnl_usd"])
            for t in rows:
                w.writerow([d, t.get("clientExtensions", {}).get("tag", ""), t["initialUnits"], t["openTime"][:19], t["price"],
                            t.get("closeTime", "")[:19], t.get("averageClosePrice", ""), t.get("realizedPL", "")])
        pnl = sum(float(t.get("realizedPL", 0)) for t in rows)
        self.say(f"Day {d}: {len(rows)} trade(s), P&L ${pnl:+.2f}, balance ${self.br.balance():,.2f}")

    def run(self):
        self.say(f"bot started — {self.cfg.get('environment', 'practice')}, risk {self.risk_pct}% per trade, "
                 f"{'DRY-RUN' if self.dry else 'sending orders'}")
        while True:
            now = datetime.now(NY); d = now.date()
            if d.weekday() < 5:
                jobs = [("prefade", at(d, 9, 0, 5), at(d, 9, 10), self.job_prefade),
                        ("opex", at(d, 9, 30, 5), at(d, 9, 35), self.job_opex),
                        ("gapfb", at(d, 9, 45, 5), at(d, 10, 25), self.job_gapfb),
                        ("close_prefade", at(d, 13, 0), at(d, 13, 10), self.job_close_prefade),
                        ("flatten", at(d, 15, 55), at(d, 15, 59), self.job_flatten),
                        ("journal", at(d, 16, 5), at(d, 16, 30), self.job_journal)]
                for name, start, end, fn in jobs:
                    if name in self.enabled and not self.enabled[name]: continue
                    key = f"done_{name}"
                    if start <= now < end and self.state.get(key) != str(d):
                        try:
                            fn(d)
                        except Exception as e:                      # keep running; retry next loop inside the window
                            log.exception("%s failed: %s", name, e); continue
                        self.state[key] = str(d); self.save()
            time.sleep(15)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(HERE / "bot.log")])
    b = Bot(load_config(), dry=a.dry_run or a.check)
    if a.check:
        today = datetime.now(NY).date(); sp = b.br.spec()
        log.info("connected: balance %.2f | %s min size %s, unit precision %s", b.br.balance(), b.br.instrument,
                 sp["minimumTradeSize"], sp["tradeUnitsPrecision"])
        log.info("GapFB now: %s", evaluate(b.br.candles_m1(5000), today)[1])
        log.info("Pre-Fade now: %s", prefade(b.br.candles("M30", 2000), today)[1])
        log.info("Opex now: %s", opex(b.br.candles("M30", 2000), today)[1])
        b.say("connection test OK")
        return
    b.run()


if __name__ == "__main__":
    main()
