ALTER TABLE collection_runs ADD COLUMN provider_id TEXT NOT NULL DEFAULT 'world_bank_wdi';
CREATE TABLE provider_cooldowns (
    provider_id TEXT PRIMARY KEY,
    not_before REAL NOT NULL,
    reason TEXT NOT NULL
);
