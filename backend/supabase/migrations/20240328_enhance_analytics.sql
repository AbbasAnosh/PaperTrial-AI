-- Enhance analytics capabilities

-- Drop existing objects if they exist
DROP MATERIALIZED VIEW IF EXISTS submission_metrics_summary;
DROP VIEW IF EXISTS submission_metrics;

-- Create submission_metrics table
CREATE TABLE submission_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    metrics JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster metrics queries
CREATE INDEX idx_submission_metrics_user_period 
ON submission_metrics(user_id, period_start, period_end);

-- Create materialized view for frequently accessed metrics
CREATE MATERIALIZED VIEW submission_metrics_summary AS
SELECT
    user_id,
    date_trunc('day', period_start) as day,
    metrics->>'total_submissions' as total_submissions,
    metrics->'status_breakdown' as status_breakdown,
    metrics->'processing_time_stats' as processing_time_stats,
    metrics->'error_breakdown' as error_breakdown,
    metrics->'retry_statistics' as retry_statistics,
    metrics->'submission_method_distribution' as method_distribution,
    metrics->'hourly_distribution' as hourly_distribution
FROM submission_metrics
WHERE version = 1;

-- Create index on materialized view
CREATE UNIQUE INDEX idx_submission_metrics_summary_user_day 
ON submission_metrics_summary(user_id, day);

-- Create function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_submission_metrics_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY submission_metrics_summary;
END;
$$ LANGUAGE plpgsql;

-- Create function to get user metrics with caching
CREATE OR REPLACE FUNCTION get_user_metrics(
    p_user_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS JSONB AS $$
DECLARE
    v_start_date TIMESTAMP WITH TIME ZONE;
    v_result JSONB;
BEGIN
    v_start_date := NOW() - (p_days || ' days')::INTERVAL;
    
    SELECT jsonb_build_object(
        'summary', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'day', day,
                    'total_submissions', total_submissions::INTEGER,
                    'status_breakdown', status_breakdown,
                    'processing_time_stats', processing_time_stats,
                    'error_breakdown', error_breakdown,
                    'retry_statistics', retry_statistics,
                    'method_distribution', method_distribution,
                    'hourly_distribution', hourly_distribution
                )
            )
            FROM submission_metrics_summary
            WHERE user_id = p_user_id
            AND day >= v_start_date
            ORDER BY day DESC
        ),
        'period', jsonb_build_object(
            'start_date', v_start_date,
            'end_date', NOW(),
            'days', p_days
        )
    ) INTO v_result;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION get_user_metrics(UUID, INTEGER) TO authenticated;
GRANT SELECT ON submission_metrics_summary TO authenticated;
GRANT ALL ON submission_metrics TO authenticated;

-- Create trigger to refresh materialized view
CREATE OR REPLACE FUNCTION trigger_refresh_submission_metrics_summary()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('refresh_submission_metrics_summary', '');
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER refresh_submission_metrics_summary_trigger
AFTER INSERT OR UPDATE ON submission_metrics
FOR EACH STATEMENT
EXECUTE FUNCTION trigger_refresh_submission_metrics_summary();

-- Add RLS policies
ALTER TABLE submission_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own metrics"
    ON submission_metrics
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own metrics"
    ON submission_metrics
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own metrics"
    ON submission_metrics
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id); 