CREATE TABLE observations (
    series_id TEXT NOT NULL,
    period_key TEXT NOT NULL,
    value TEXT NOT NULL,
    provider_status TEXT NOT NULL,
    footnote TEXT NOT NULL,
    source_url TEXT NOT NULL,
    dataset_updated_on TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    retained INTEGER NOT NULL DEFAULT 0 CHECK(retained IN (0, 1)),
    PRIMARY KEY (series_id, period_key)
);
CREATE TABLE collection_runs (
    id INTEGER PRIMARY KEY,
    group_id TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    completed_at TEXT,
    outcome TEXT NOT NULL CHECK(outcome IN ('running', 'ok', 'error')),
    error_kind TEXT,
    window_start INTEGER NOT NULL,
    window_end INTEGER NOT NULL
);
CREATE INDEX collection_group_time ON collection_runs(group_id, id DESC);
CREATE UNIQUE INDEX one_running_group ON collection_runs(group_id) WHERE outcome = 'running';
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1))
);
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    revoked_at INTEGER,
    confirmed_at INTEGER
);
CREATE INDEX session_expiry ON sessions(expires_at);
CREATE TABLE refresh_tokens (
    digest TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    state TEXT NOT NULL CHECK(state IN ('active', 'pending', 'retired')),
    created_at INTEGER NOT NULL,
    retired_at INTEGER
);
CREATE UNIQUE INDEX one_active_token ON refresh_tokens(session_id) WHERE state = 'active';
CREATE UNIQUE INDEX one_pending_token ON refresh_tokens(session_id) WHERE state = 'pending';
