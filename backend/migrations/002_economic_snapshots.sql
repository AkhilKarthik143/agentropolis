CREATE TABLE IF NOT EXISTS economic_snapshots (
    session_id TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS economy_events_session_seq ON economy_events(session_id, seq);
