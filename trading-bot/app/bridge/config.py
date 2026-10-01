"""Settings (environment) and accounts (accounts.json)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field

POINT_VALUE = {"MNQ": 2.0, "NQ": 20.0, "MES": 5.0, "ES": 50.0, "M2K": 5.0, "RTY": 50.0, "MYM": 0.5, "YM": 5.0}


def point_value(symbol: str) -> float:
    """$ per point for a TradingView ticker like 'MNQ1!' or 'CME_MINI:MNQZ2026'."""
    root = symbol.split(":")[-1].rstrip("!").rstrip("0123456789")
    for k in sorted(POINT_VALUE, key=len, reverse=True):
        if root.startswith(k):
            return POINT_VALUE[k]
    return 1.0


class Rules(BaseModel):
    """Prop-firm guard rails. Exits are never blocked — only new entries."""
    entry_start: str = "09:30"          # New York time
    entry_end: str = "15:30"
    flatten_at: str = "15:55"           # the bridge sends a close to every open account at this time
    max_contracts: int = 2
    max_trades_per_day: int = 3
    daily_loss_limit: float = 600.0     # estimated realized $ loss that blocks new entries for the day
    trailing_dd: float = 2000.0         # Lucid 50K end-of-day trailing drawdown
    dd_buffer: float = 300.0            # block entries when room to the drawdown is below this
    profit_target: float = 3000.0       # stop opening trades once reached (eval passed); 0 = off


class Account(BaseModel):
    id: str
    name: str = ""
    enabled: bool = False
    multiplier: float = 1.0
    url: str = "https://api.pickmytrade.io/v2/add-trade-data"   # check it against your PickMyTrade dashboard
    template_open: dict = Field(default_factory=dict)   # JSON from PickMyTrade's alert builder, with {{placeholders}}
    template_close: dict = Field(default_factory=dict)
    rules: Rules = Field(default_factory=Rules)


class Settings(BaseModel):
    webhook_secret: str = ""
    admin_user: str = "admin"
    admin_pass: str = ""
    dry_run: bool = True
    db_path: str = "bridge.db"
    accounts_path: str = "accounts.json"


def load_settings() -> Settings:
    e = os.environ
    return Settings(
        webhook_secret=e.get("BRIDGE_SECRET", ""),
        admin_user=e.get("BRIDGE_ADMIN_USER", "admin"),
        admin_pass=e.get("BRIDGE_ADMIN_PASS", ""),
        dry_run=e.get("BRIDGE_DRY_RUN", "1") != "0",
        db_path=e.get("BRIDGE_DB", "bridge.db"),
        accounts_path=e.get("BRIDGE_ACCOUNTS", "accounts.json"),
    )


def load_accounts(path: str) -> list[Account]:
    p = Path(path)
    if not p.exists():
        return []
    return [Account(**a) for a in json.loads(p.read_text(encoding="utf-8"))]
