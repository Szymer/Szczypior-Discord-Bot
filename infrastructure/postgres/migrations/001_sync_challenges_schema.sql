-- Align existing PostgreSQL schema with the current db-service models.
-- Safe to run multiple times.

BEGIN;

ALTER TABLE public.challenges
    ADD COLUMN IF NOT EXISTS rules JSONB,
    ADD COLUMN IF NOT EXISTS discord_channel_id TEXT;

ALTER TABLE public.challenges
    ALTER COLUMN is_active SET DEFAULT TRUE,
    ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE public.activity_rules
    ALTER COLUMN emoji SET DEFAULT '🏃',
    ALTER COLUMN base_points SET DEFAULT 0,
    ALTER COLUMN unit SET DEFAULT 'km',
    ALTER COLUMN min_distance SET DEFAULT 0.0,
    ALTER COLUMN bonuses SET DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_activity_rules_challenge_id
    ON public.activity_rules (challenge_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'activity_rules_challenge_id_activity_type_key'
          AND conrelid = 'public.activity_rules'::regclass
    ) THEN
        ALTER TABLE public.activity_rules
            ADD CONSTRAINT activity_rules_challenge_id_activity_type_key
            UNIQUE (challenge_id, activity_type);
    END IF;
END $$;

COMMENT ON TABLE public.challenges IS 'Challenges with rules and active status';
COMMENT ON COLUMN public.challenges.rules IS 'JSONB field to store challenge rules';
COMMENT ON COLUMN public.challenges.discord_channel_id IS 'Discord channel ID assigned to the challenge';
COMMENT ON TABLE public.activity_rules IS 'Per-challenge activity type rules';
COMMENT ON COLUMN public.activity_rules.bonuses IS 'JSONB array of bonus names: ["obciążenie","przewyższenie"]';

COMMIT;