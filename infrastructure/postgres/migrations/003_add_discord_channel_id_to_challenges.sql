-- Migration: 003
-- Add discord_channel_id column to challenges table
ALTER TABLE challenges ADD COLUMN IF NOT EXISTS discord_channel_id TEXT;
