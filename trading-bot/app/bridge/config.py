"""App settings (settings.json) and connections (accounts.json), both in the app's data folder."""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from pydantic import BaseModel, Field

BRAND = "TRADEBRIDGE"          # placeholder name — change it here and in static/index.html

POINT_VALUE = {"MNQ": 2.0, "NQ": 20.0, "MES": 5.0, "ES": 50.0, "M2K": 5.0, "RTY": 50.0, "MYM": 0.5, "YM": 5.0,
               "MGC": 10.0, "GC": 100.0, "MCL": 100.0, "CL": 1000.0}
TO_MICRO = {"NQ": "MNQ", "ES": "MES", "RTY": "M2K", "YM": "MYM", "GC": "MGC", "CL": "MCL"}


def _root(symbol: str) -> tuple[str, str]:
    """'CME_MINI:MNQZ2026' → ('MNQ', 'Z2026'); 'MNQ1!' → ('MNQ', '1!')."""
    s = symbol.split(":")[-1]
    for k in sorted(POINT_VALUE, key=len, reverse=True):
        if s.startswith(k):
            return k, s[len(k):]
    return s, ""


def point_value(symbol: str) -> float:
    return POINT_VALUE.get(_root(symbol)[0], 1.0)


def to_micro(symbol: str) -> str:
    root, rest = _root(symbol)
    return TO_MICRO.get(root, root) + rest if root in TO_MICRO else symbol


class Rules(BaseModel):
    """Prop-firm guard rails. Exits are never blocked — only new entries."""
    entry_start: str = "09:30"          # New York time
    entry_end: str = "15:30"
    flatten_at: str = "15:55"           # close everything at this time
    max_contracts: int = 2
    max_trades_per_day: int = 3
    daily_loss_limit: float = 600.0     # estimated realized $ loss that blocks new entries for the day
    trailing_dd: float = 2000.0         # e.g. Lucid 50K end-of-day trailing drawdown
    dd_buffer: float = 300.0            # block entries when room to the drawdown is below this
    profit_target: float = 3000.0       # stop opening trades once reached (eval passed); 0 = off


class Account(BaseModel):
    id: str
    name: str = ""
    group: str = ""
    broker_account: str = ""            # shown in the table, e.g. the Tradovate account number
    enabled: bool = False               # "Follow"
    multiplier: float = 1.0             # "Ratio"
    micros_only: bool = False           # NQ → MNQ, ES → MES …
    url: str = "https://api.pickmytrade.io/v2/add-trade-data"
    template_open: dict = Field(default_factory=dict)   # JSON from PickMyTrade's alert builder, with {{placeholders}}
    template_close: dict = Field(default_factory=dict)
    template_cancel: dict = Field(default_factory=dict)
    rules: Rules = Field(default_factory=Rules)


class Settings(BaseModel):
    webhook_secret: str = ""
    admin_token: str = ""               # the dashboard's session key (random per start unless set)
    dry_run: bool = True
    port: int = 8000
    news_blackout_min: int = 0          # block entries this many minutes around high-impact USD news (0 = off)
    public_url: str = ""                # the address TradingView posts to (tunnel / VPS), shown in the setup
    home: str = "."

    @property
    def db_path(self) -> str:
        return str(Path(self.home) / "bridge.db")

    @property
    def accounts_path(self) -> str:
        return str(Path(self.home) / "accounts.json")

    @property
    def settings_path(self) -> str:
        return str(Path(self.home) / "settings.json")

    def save(self):
        keep = self.model_dump(exclude={"admin_token", "home"})
        Path(self.settings_path).write_text(json.dumps(keep, indent=2), encoding="utf-8")


def load_settings(home: str | None = None, use_env: bool = True) -> Settings:
    """use_env=False for per-user settings in the web edition: one env secret must never be shared by every user."""
    e = os.environ if use_env else {}
    home = home or os.environ.get("BRIDGE_HOME", ".")
    Path(home).mkdir(parents=True, exist_ok=True)
    p = Path(home) / "settings.json"
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    s = Settings(**data, home=home)
    if e.get("BRIDGE_SECRET"):
        s.webhook_secret = e["BRIDGE_SECRET"]
    if e.get("BRIDGE_DRY_RUN") is not None:
        s.dry_run = e["BRIDGE_DRY_RUN"] != "0"
    if not s.webhook_secret:
        s.webhook_secret = secrets.token_urlsafe(18)
    s.admin_token = e.get("BRIDGE_TOKEN") or secrets.token_urlsafe(24)
    s.save()
    return s


def load_accounts(path: str) -> list[Account]:
    p = Path(path)
    if not p.exists():
        return []
    return [Account(**a) for a in json.loads(p.read_text(encoding="utf-8"))]


def save_accounts(path: str, accounts: list[Account]):
    Path(path).write_text(json.dumps([a.model_dump() for a in accounts], indent=2), encoding="utf-8")
