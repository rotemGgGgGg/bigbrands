-- Every message the bot read, and what it decided. A skipped signal is kept
-- with its reason: the gaps in what the bot understood are part of the record.
CREATE TABLE IF NOT EXISTS signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          INTEGER NOT NULL,            -- unix seconds the message arrived
    side        TEXT,                        -- buy | sell
    order_type  TEXT,                        -- market | stop | limit
    entry       REAL,
    sl          REAL,
    tp          REAL,
    status      TEXT NOT NULL,               -- taken | skipped | failed
    reason      TEXT,
    raw         TEXT
);
CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals (ts);

-- Positions. A stop or limit order waits as pending until price reaches it,
-- and expires if it never does, because that is what the order would do.
CREATE TABLE IF NOT EXISTS trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id   INTEGER,
    mode        TEXT NOT NULL,               -- paper | live
    side        TEXT NOT NULL,
    order_type  TEXT NOT NULL,
    units       REAL NOT NULL,
    entry       REAL NOT NULL,
    sl          REAL NOT NULL,
    tp          REAL NOT NULL,
    created_at  INTEGER NOT NULL,
    opened_at   INTEGER,                     -- null while pending
    closed_at   INTEGER,
    exit        REAL,
    state       TEXT NOT NULL,               -- pending | open | closed | expired
    outcome     TEXT,                        -- tp | sl | manual
    pips        REAL,
    pnl         REAL,
    note        TEXT,
    checked_to  INTEGER                      -- how far paper settlement has looked
);
CREATE INDEX IF NOT EXISTS idx_trades_state ON trades (state);
CREATE INDEX IF NOT EXISTS idx_trades_created ON trades (created_at);

-- Small facts about the bot itself: when it last spoke, in which mode.
CREATE TABLE IF NOT EXISTS meta (
    k   TEXT PRIMARY KEY,
    v   TEXT,
    ts  INTEGER
);
