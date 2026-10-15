-- GDP keeps its existing columns and insert contract. Other groups additionally
-- persist validated measurement semantics, so methodology cannot be relabelled
-- by a later catalogue change. Unknown provider update dates are SQL NULL.
ALTER TABLE observations RENAME TO observations_old;
CREATE TABLE observations (
    series_id TEXT NOT NULL,
    period_key TEXT NOT NULL,
    value TEXT NOT NULL,
    provider_status TEXT NOT NULL,
    footnote TEXT NOT NULL,
    source_url TEXT NOT NULL,
    dataset_updated_on TEXT,
    retrieved_at TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    retained INTEGER NOT NULL DEFAULT 0 CHECK(retained IN (0, 1)),
    group_id TEXT NOT NULL DEFAULT 'gdp',
    measurement_json TEXT CHECK(measurement_json IS NULL OR json_valid(measurement_json)),
    PRIMARY KEY (series_id, period_key)
);
INSERT INTO observations SELECT *, 'gdp', NULL FROM observations_old;
DROP TABLE observations_old;
CREATE INDEX observations_group ON observations(group_id, period_key);
