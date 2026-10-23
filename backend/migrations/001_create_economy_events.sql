CREATE TABLE IF NOT EXISTS economy_events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    type TEXT NOT NULL,
    session_id TEXT,
    business_id TEXT,
    deal_id TEXT,
    correlation_id TEXT,
    causation_id TEXT,
    idempotency_key TEXT UNIQUE,
    payload TEXT NOT NULL,
    prev_hash TEXT,
    hash TEXT
);
