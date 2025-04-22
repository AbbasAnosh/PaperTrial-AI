-- Minimal changes to enhance submission processing
-- This is a simplified version that should work with Supabase's permission model

-- Add error tracking columns to form_submissions
ALTER TABLE IF EXISTS form_submissions
ADD COLUMN IF NOT EXISTS error_category TEXT,
ADD COLUMN IF NOT EXISTS error_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS error_details JSONB,
ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS processing_completed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS processing_duration_ms INTEGER,
ADD COLUMN IF NOT EXISTS retry_backoff_seconds INTEGER DEFAULT 60,
ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS external_service_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS external_service_response JSONB; 