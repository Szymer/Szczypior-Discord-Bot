-- ============================================================================
-- SZCZYPIOR DISCORD BOT - Database Schema
-- ============================================================================
-- Version: 1.0
-- Description: PostgreSQL schema for activity tracking with special missions
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: users
-- ============================================================================
-- Stores Discord user information
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    discord_id TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    username TEXT,
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_discord_id ON users(discord_id);
CREATE INDEX idx_users_display_name ON users(display_name);

COMMENT ON TABLE users IS 'Discord users participating in fitness challenge';
COMMENT ON COLUMN users.discord_id IS 'Unique Discord user ID';
COMMENT ON COLUMN users.display_name IS 'Display name (nick) used in rankings';

-- ============================================================================
-- TABLE: special_missions
-- ============================================================================
-- Stores special mission definitions (monthly challenges)
CREATE TABLE IF NOT EXISTS special_missions (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    emoji TEXT DEFAULT '💥',
    bonus_points INTEGER NOT NULL DEFAULT 0,
    min_distance_km NUMERIC(10, 2),
    min_time_minutes INTEGER,
    activity_type_filter TEXT,
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    max_completions_per_user INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_valid_date_range CHECK (valid_from < valid_until),
    CONSTRAINT chk_bonus_points_positive CHECK (bonus_points >= 0)
);

CREATE INDEX idx_special_missions_active ON special_missions(is_active, valid_from, valid_until);
CREATE INDEX idx_special_missions_dates ON special_missions(valid_from, valid_until);

COMMENT ON TABLE special_missions IS 'Special monthly missions with bonus points';
COMMENT ON COLUMN special_missions.activity_type_filter IS 'NULL = all types, or specific type like "bieganie_teren"';
COMMENT ON COLUMN special_missions.max_completions_per_user IS 'How many times user can complete this mission';

-- ============================================================================
-- TABLE: activities
-- ============================================================================
-- Stores user fitness activities with full point breakdown
CREATE TABLE IF NOT EXISTS activities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    iid TEXT UNIQUE NOT NULL,
    activity_type TEXT NOT NULL,
    distance_km NUMERIC(10, 2) NOT NULL,
    weight_kg NUMERIC(10, 2),
    elevation_m INTEGER,
    time_minutes INTEGER,
    pace TEXT,
    heart_rate_avg INTEGER,
    calories INTEGER,
    base_points INTEGER NOT NULL DEFAULT 0,
    weight_bonus_points INTEGER DEFAULT 0,
    elevation_bonus_points INTEGER DEFAULT 0,
    special_mission_id INTEGER REFERENCES special_missions(id) ON DELETE SET NULL,
    mission_bonus_points INTEGER DEFAULT 0,
    total_points INTEGER NOT NULL DEFAULT 0,
    challenge_id INTEGER REFERENCES challenges(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    message_id TEXT,
    message_timestamp TEXT,
    ai_comment TEXT,
    CONSTRAINT chk_distance_positive CHECK (distance_km > 0),
    CONSTRAINT chk_points_non_negative CHECK (
        base_points >= 0 AND 
        weight_bonus_points >= 0 AND 
        elevation_bonus_points >= 0 AND
        mission_bonus_points >= 0 AND
        total_points >= 0
    ),
    CONSTRAINT chk_activity_type CHECK (
        activity_type IN (
            'bieganie_teren', 
            'bieganie_bieznia', 
            'plywanie', 
            'rower', 
            'spacer', 
            'cardio'
        )
    )
);

CREATE INDEX idx_activities_user_id ON activities(user_id);
CREATE INDEX idx_activities_created_at ON activities(created_at DESC);
CREATE INDEX idx_activities_iid ON activities(iid);
CREATE INDEX idx_activities_type ON activities(activity_type);
CREATE INDEX idx_activities_mission ON activities(special_mission_id) WHERE special_mission_id IS NOT NULL;
CREATE INDEX idx_activities_message_id ON activities(message_id) WHERE message_id IS NOT NULL;
CREATE INDEX idx_activities_challenge ON activities(challenge_id);

COMMENT ON TABLE activities IS 'User fitness activities with complete point calculation';
COMMENT ON COLUMN activities.iid IS 'Unique ID from Discord: timestamp_messageid';
COMMENT ON COLUMN activities.base_points IS 'Base points from distance * activity multiplier';
COMMENT ON COLUMN activities.weight_bonus_points IS 'Bonus for carrying weight (>5kg)';
COMMENT ON COLUMN activities.elevation_bonus_points IS 'Bonus for elevation gain';
COMMENT ON COLUMN activities.mission_bonus_points IS 'Bonus from completing special mission';
COMMENT ON COLUMN activities.total_points IS 'Sum of all point types';
COMMENT ON COLUMN activities.challenge_id IS 'Foreign key to challenges table';

-- ============================================================================
-- TABLE: challenges
-- ============================================================================
-- Stores information about challenges
CREATE TABLE IF NOT EXISTS challenges (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    rules JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE challenges IS 'Challenges with rules and active status';
COMMENT ON COLUMN challenges.rules IS 'JSONB field to store challenge rules';

-- ============================================================================
-- TABLE: challenge_participants
-- ============================================================================
-- Tracks participants in challenges
CREATE TABLE IF NOT EXISTS challenge_participants (
    id SERIAL PRIMARY KEY,
    challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE challenge_participants IS 'Participants of challenges';
COMMENT ON COLUMN challenge_participants.joined_at IS 'Timestamp when the user joined the challenge';

-- ============================================================================
-- VIEWS
-- ============================================================================

-- User rankings with total points
CREATE OR REPLACE VIEW user_rankings AS
SELECT 
    u.id,
    u.discord_id,
    u.display_name,
    COUNT(a.id) AS total_activities,
    COALESCE(SUM(a.distance_km), 0) AS total_distance_km,
    COALESCE(SUM(a.total_points), 0) AS total_points,
    COALESCE(SUM(a.base_points), 0) AS base_points,
    COALESCE(SUM(a.weight_bonus_points), 0) AS weight_bonus_points,
    COALESCE(SUM(a.elevation_bonus_points), 0) AS elevation_bonus_points,
    COALESCE(SUM(a.mission_bonus_points), 0) AS mission_bonus_points,
    MAX(a.created_at) AS last_activity_at
FROM users u
LEFT JOIN activities a ON u.id = a.user_id
GROUP BY u.id, u.discord_id, u.display_name
ORDER BY total_points DESC;

COMMENT ON VIEW user_rankings IS 'Aggregated user statistics and rankings';

-- Activity statistics by type
CREATE OR REPLACE VIEW activity_type_stats AS
SELECT 
    activity_type,
    COUNT(*) AS activity_count,
    COUNT(DISTINCT user_id) AS unique_users,
    ROUND(AVG(distance_km), 2) AS avg_distance_km,
    SUM(distance_km) AS total_distance_km,
    ROUND(AVG(total_points), 0) AS avg_points,
    SUM(total_points) AS total_points
FROM activities
GROUP BY activity_type
ORDER BY total_points DESC;

COMMENT ON VIEW activity_type_stats IS 'Statistics grouped by activity type';

-- Mission completion status
CREATE OR REPLACE VIEW mission_completions AS
SELECT 
    sm.id AS mission_id,
    sm.name AS mission_name,
    sm.bonus_points,
    sm.valid_from,
    sm.valid_until,
    COUNT(DISTINCT a.user_id) AS unique_completions,
    COUNT(a.id) AS total_completions,
    SUM(a.mission_bonus_points) AS total_bonus_awarded
FROM special_missions sm
LEFT JOIN activities a ON sm.id = a.special_mission_id
GROUP BY sm.id, sm.name, sm.bonus_points, sm.valid_from, sm.valid_until
ORDER BY sm.valid_from DESC;

COMMENT ON VIEW mission_completions IS 'Special mission completion statistics';

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to users
DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply updated_at trigger to special_missions
DROP TRIGGER IF EXISTS trigger_special_missions_updated_at ON special_missions;
CREATE TRIGGER trigger_special_missions_updated_at
    BEFORE UPDATE ON special_missions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Insert example special mission (Grudzień 2025)
INSERT INTO special_missions (
    name, 
    description, 
    emoji,
    bonus_points, 
    min_distance_km,
    activity_type_filter,
    valid_from, 
    valid_until,
    is_active
) VALUES (
    'Rozruch Zimowy ❄️',
    'Wykonaj dowolną aktywność ciągłą na dystansie min. 5 km',
    '❄️',
    2000,
    5.0,
    NULL, -- any activity type
    '2025-12-01 00:00:00+00',
    '2025-12-31 23:59:59+00',
    TRUE
) ON CONFLICT DO NOTHING;

-- ============================================================================
-- HELPER QUERIES (COMMENT OUT AFTER SETUP)
-- ============================================================================

-- Example: Get user by Discord ID (create if not exists pattern)
-- INSERT INTO users (discord_id, display_name) 
-- VALUES ('123456789', 'TestUser') 
-- ON CONFLICT (discord_id) DO UPDATE SET display_name = EXCLUDED.display_name
-- RETURNING *;

-- Example: Insert activity with mission check
-- WITH mission AS (
--     SELECT id, bonus_points 
--     FROM special_missions 
--     WHERE is_active = TRUE 
--       AND CURRENT_TIMESTAMP BETWEEN valid_from AND valid_until
--       AND (activity_type_filter IS NULL OR activity_type_filter = 'bieganie_teren')
--       AND 5.0 >= COALESCE(min_distance_km, 0)
--     LIMIT 1
-- )
-- INSERT INTO activities (
--     user_id, iid, activity_type, distance_km, 
--     base_points, total_points, created_at,
--     special_mission_id, mission_bonus_points
-- ) VALUES (
--     1, '1234567890_9876543210', 'bieganie_teren', 10.0,
--     10000, 10000 + COALESCE((SELECT bonus_points FROM mission), 0),
--     CURRENT_TIMESTAMP,
--     (SELECT id FROM mission), 
--     COALESCE((SELECT bonus_points FROM mission), 0)
-- );

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
