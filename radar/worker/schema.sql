-- Who bought what, recently. One row per wallet per mint; the cluster rule
-- reads this back to see how many wallets have landed on the same token.
CREATE TABLE IF NOT EXISTS buys (
    mint      TEXT NOT NULL,
    wallet    TEXT NOT NULL,
    name      TEXT NOT NULL,
    sol       REAL NOT NULL,
    ts        INTEGER NOT NULL,
    is_signal INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (mint, wallet)
);
CREATE INDEX IF NOT EXISTS idx_buys_mint_ts ON buys (mint, ts);

-- What has already been said, so a repeat does not reach the phone twice.
CREATE TABLE IF NOT EXISTS sent (
    key TEXT PRIMARY KEY,
    ts  INTEGER NOT NULL
);

-- The alert log, kept for calibrating thresholds against outcomes later.
CREATE TABLE IF NOT EXISTS alerts (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    kind    TEXT NOT NULL,
    mint    TEXT NOT NULL,
    wallets INTEGER NOT NULL,
    score   INTEGER,
    ts      INTEGER NOT NULL,
    payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts (ts);
