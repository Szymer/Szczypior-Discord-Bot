CREATE TABLE IF NOT EXISTS activities (
    iid TEXT PRIMARY KEY,
    nick TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    distance_km NUMERIC(10, 2) NOT NULL,
    weight_kg NUMERIC(10, 2),
    elevation_m INTEGER,
    points INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    message_id TEXT
);
