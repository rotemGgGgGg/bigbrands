-- D1 schema. Mirrors the SQLite schema the Python version uses.
CREATE TABLE IF NOT EXISTS buys (
    sig        TEXT NOT NULL,
    wallet     TEXT NOT NULL,
    mint       TEXT NOT NULL,
    ts         REAL NOT NULL,
    sol_spent  REAL NOT NULL,
    amount     REAL NOT NULL,
    PRIMARY KEY (sig, wallet, mint)
);
CREATE INDEX IF NOT EXISTS idx_buys_mint_ts ON buys (mint, ts);

CREATE TABLE IF NOT EXISTS mint_seen (
    mint       TEXT PRIMARY KEY,
    first_seen REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    mint         TEXT NOT NULL,
    ts           REAL NOT NULL,
    score        INTEGER NOT NULL,
    wallet_count INTEGER NOT NULL,
    payload      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alerts_mint_ts ON alerts (mint, ts);

-- Wallet nicknames, loaded from the tracker export so alerts stay readable.
CREATE TABLE IF NOT EXISTS wallets (
    address TEXT PRIMARY KEY,
    name    TEXT NOT NULL
);
