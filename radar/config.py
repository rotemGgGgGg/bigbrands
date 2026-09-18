"""Configuration. Everything is overridable via environment variables (.env)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _get_int(name: str, default: int) -> int:
    return int(_get(name, str(default)))


def _get_float(name: str, default: float) -> float:
    return float(_get(name, str(default)))


def _get_bool(name: str, default: bool) -> bool:
    return _get(name, "1" if default else "0").lower() in ("1", "true", "yes")


# --- Solana RPC -------------------------------------------------------------
HELIUS_API_KEY = _get("HELIUS_API_KEY", "")
RPC_URL = _get(
    "RPC_URL",
    f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    if HELIUS_API_KEY
    else "https://api.mainnet-beta.solana.com",
)
# Requests per second we allow ourselves. Helius free tier is ~10 rps; the
# public endpoint is far stricter, so we default low and let users raise it.
RPC_RPS = _get_float("RPC_RPS", 8.0 if HELIUS_API_KEY else 2.0)
RPC_TIMEOUT = _get_float("RPC_TIMEOUT", 20.0)

# --- Wallet universe --------------------------------------------------------
WALLETS_FILE = BASE_DIR / "data" / "wallets.json"
X_ACCOUNTS_FILE = BASE_DIR / "data" / "x_accounts.json"
# The tracker export marks a subset with alertsOnToast=true. Set this to 1 to
# watch only those (177 of 593) when RPC budget is tight.
ONLY_PRIORITY_WALLETS = _get_bool("ONLY_PRIORITY_WALLETS", False)
MAX_WALLETS = _get_int("MAX_WALLETS", 0)  # 0 = no cap
# Wallets with no transaction in this many days are skipped in the scan loop
# (they still get re-checked on every restart). 0 disables the skip.
SKIP_STALE_DAYS = _get_int("SKIP_STALE_DAYS", 30)

# --- Confluence detection ---------------------------------------------------
WINDOW_MINUTES = _get_int("WINDOW_MINUTES", 10)
MIN_WALLETS = _get_int("MIN_WALLETS", 3)
MIN_SOL_BUY = _get_float("MIN_SOL_BUY", 0.05)  # ignore dust buys
CHECK_INTERVAL_SEC = _get_int("CHECK_INTERVAL_SEC", 20)
# Do not re-alert the same mint unless this much time passed or the wallet
# count grew by RE_ALERT_WALLET_DELTA.
RE_ALERT_MINUTES = _get_int("RE_ALERT_MINUTES", 60)
RE_ALERT_WALLET_DELTA = _get_int("RE_ALERT_WALLET_DELTA", 2)
MIN_SCORE_TO_ALERT = _get_int("MIN_SCORE_TO_ALERT", 50)

# Mints we never care about (SOL, stables, LSTs).
IGNORED_MINTS = {
    "So11111111111111111111111111111111111111112",   # wSOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",   # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",   # USDT
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",    # mSOL
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",   # jitoSOL
}

# --- Storage ----------------------------------------------------------------
DB_PATH = Path(_get("DB_PATH", str(BASE_DIR / "radar.db")))

# --- Telegram ---------------------------------------------------------------
TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = _get("TELEGRAM_CHAT_ID", "")
