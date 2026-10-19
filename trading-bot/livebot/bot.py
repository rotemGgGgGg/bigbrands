"""GapFB-NQ live bot (OANDA NAS100_USD). Runs forever; all times New York.
  09:45:05  evaluate the day → place ONE resting stop-entry order (GTD 10:30) with a 2×ATR stop and 5×ATR trailing stop
  15:55:00  close any open position (and cancel leftovers)
  16:05:00  append today's closed trades to journal.csv
Usage:  python3 bot.py               (runs the schedule)
        python3 bot.py --check       (connects, prints balance and what it WOULD do right now; sends nothing)
        python3 bot.py --dry-run     (full schedule, but logs orders instead of sending them)"""
from __future__ import annotations

import argparse, csv, json, logging, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path

from broker_oanda import Oanda
from strategy import NY, evaluate

HERE = Path(__file__).resolve().parent
log = logging.getLogger("gapfb")


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
        self.state_path = HERE / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}

    def save(self):
        self.state_path.write_text(json.dumps(self.state, indent=1))

    # ---- 09:45 ----
    def arm(self, today: date):
        if self.state.get("armed") == str(today):
            log.info("already handled today"); return
        sig, why = evaluate(self.br.candles_m1(5000), today)
        self.state["armed"] = str(today); self.save()
        if sig is None:
            log.info("NO TRADE %s: %s", today, why); return
        bal = self.br.balance()
        risk_usd = bal * float(self.cfg.get("risk_pct", 1.0)) / 100
        units = self.br.units_for_risk(risk_usd, sig.stop_distance)
        side = "LONG" if sig.side == 1 else "SHORT"
        log.info("SIGNAL %s %s gap %+.2f%% score %d | stop-entry %.2f | ATR %.2f stop %.2f trail %.2f | risk $%.2f → %s units",
                 today, side, sig.gap * 100, sig.score, sig.level, sig.atr, sig.stop_distance, sig.trail_distance, risk_usd, units)
        if units <= 0:
            log.warning("position size below the broker minimum — skipped (raise risk_pct or the balance)"); return
        if self.dry:
            log.info("[dry-run] order not sent"); return
        r = self.br.place_stop_entry(sig.side, units, sig.level, sig.stop_distance, sig.trail_distance, at(today, 10, 30))
        log.info("order placed: %s", json.dumps(r.get("orderCreateTransaction", r))[:400])

    # ---- 15:55 ----
    def flatten(self, today: date):
        if self.dry:
            log.info("[dry-run] would close position / cancel pending"); return
        n = self.br.cancel_pending()
        r = self.br.close_position()
        log.info("15:55 flat: cancelled %d pending, close → %s", n, "nothing open" if r is None else "closed")

    # ---- 16:05 ----
    def journal(self, today: date):
        path = HERE / "journal.csv"; new = not path.exists()
        rows = [t for t in self.br.closed_trades(20) if t.get("closeTime", "")[:10] == str(today)]
        with path.open("a", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(["date", "units", "open_time", "entry", "close_time", "exit", "pnl_usd"])
            for t in rows:
                w.writerow([today, t["initialUnits"], t["openTime"][:19], t["price"], t.get("closeTime", "")[:19],
                            t.get("averageClosePrice", ""), t.get("realizedPL", "")])
        log.info("journal: %d closed trade(s) today", len(rows))

    def run(self):
        log.info("bot started (%s, %s, risk %s%%)", self.cfg.get("environment", "practice"), "DRY-RUN" if self.dry else "LIVE ORDERS",
                 self.cfg.get("risk_pct", 1.0))
        while True:
            now = datetime.now(NY); d = now.date()
            if d.weekday() < 5:
                jobs = [(at(d, 9, 45, 5), at(d, 10, 25), self.arm), (at(d, 15, 55), at(d, 15, 59), self.flatten),
                        (at(d, 16, 5), at(d, 16, 30), self.journal)]
                for start, end, fn in jobs:
                    key = f"done_{fn.__name__}"
                    if start <= now < end and self.state.get(key) != str(d):
                        try:
                            fn(d)
                        except Exception as e:                       # keep running; retry next minute
                            log.exception("%s failed: %s", fn.__name__, e); continue
                        self.state[key] = str(d); self.save()
            time.sleep(20)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(HERE / "bot.log")])
    b = Bot(load_config(), dry=a.dry_run or a.check)
    if a.check:
        log.info("connected: balance %.2f, instrument %s (min size %s, precision %s)", b.br.balance(), b.br.instrument,
                 b.br.spec()["minimumTradeSize"], b.br.spec()["tradeUnitsPrecision"])
        today = datetime.now(NY).date()
        sig, why = evaluate(b.br.candles_m1(5000), today)
        log.info("today's evaluation with data so far: %s", why if sig is None else sig)
        return
    b.run()


if __name__ == "__main__":
    main()
