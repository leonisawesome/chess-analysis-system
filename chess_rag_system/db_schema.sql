-- Database schema for chess deduplication system
-- Run this once to set up the PostgreSQL database

-- Create database if not exists (run as superuser)
-- CREATE DATABASE chess_dedup;

-- Connect to the database
-- \c chess_dedup;

-- Main deduplication table
CREATE TABLE IF NOT EXISTS game_hashes (
    hash VARCHAR(64) PRIMARY KEY,
    bundle_path TEXT,
    bundle_offset INTEGER,
    game_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_game_hashes_created
ON game_hashes(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_game_hashes_bundle
ON game_hashes(bundle_path);

-- Optional: Track deduplication statistics
CREATE TABLE IF NOT EXISTS dedup_stats (
    id SERIAL PRIMARY KEY,
    batch_id UUID DEFAULT gen_random_uuid(),
    total_processed INTEGER NOT NULL,
    duplicates_found INTEGER NOT NULL,
    errors INTEGER NOT NULL,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Optional: Error log for malformed PGNs
CREATE TABLE IF NOT EXISTS dedup_errors (
    id SERIAL PRIMARY KEY,
    file_path TEXT,
    error_message TEXT,
    pgn_snippet TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Grant permissions (adjust username as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO chess_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO chess_user;