-- Latest canonical quote/status only; no invented intraday histories.
CREATE TABLE market_quotes (
    instrument_id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    retained INTEGER NOT NULL DEFAULT 0 CHECK (retained IN (0, 1))
);
CREATE TABLE market_sessions (
    exchange TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    retained INTEGER NOT NULL DEFAULT 0 CHECK (retained IN (0, 1))
);
