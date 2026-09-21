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

-- What happened next.
--
-- Every question worth asking about this radar is about outcomes, and none
-- of them could be answered: the alerts recorded what was sent and never
-- what it was worth. Survival could be checked after the fact, but return
-- could not, because the price at the moment of the alert was gone.
-- So it is written down now, and checked again later.
CREATE TABLE IF NOT EXISTS outcomes (
    mint       TEXT PRIMARY KEY,
    alert_ts   INTEGER NOT NULL,
    -- the cluster as it looked when it fired, so factors can be tested
    people     INTEGER,
    wallets    INTEGER,
    sol        REAL,
    max_sol    REAL,
    span_s     INTEGER,
    selective  INTEGER,
    score      INTEGER,
    -- the market at that moment
    entry_price REAL,
    entry_mc    REAL,
    entry_liq   REAL,
    -- and at each horizon after it
    p5m   REAL, mc5m   REAL, liq5m   REAL,
    p1h   REAL, mc1h   REAL, liq1h   REAL,
    p24h  REAL, mc24h  REAL, liq24h  REAL
);
CREATE INDEX IF NOT EXISTS idx_outcomes_ts ON outcomes (alert_ts);
