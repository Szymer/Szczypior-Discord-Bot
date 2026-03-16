-- Migration: 002
-- Add role column to users table for dashboard authorization
ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user';
