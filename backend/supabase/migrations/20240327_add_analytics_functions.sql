-- Add analytics functions for tracking form processing metrics

-- Function to get submission metrics
CREATE OR REPLACE FUNCTION get_submission_metrics(
    user_id UUID,
    days INTEGER DEFAULT 30
) RETURNS JSONB AS $$
DECLARE
    start_date TIMESTAMP WITH TIME ZONE;
    result JSONB;
BEGIN
    start_date := NOW() - (days || ' days')::INTERVAL;
    
    WITH metrics AS (
        SELECT
            COUNT(*) as total_submissions,
            jsonb_object_agg(
                status,
                COUNT(*)
            ) as status_counts,
            AVG(processing_duration_ms) as avg_processing_time_ms,
            jsonb_object_agg(
                error_category,
                COUNT(*)
            ) FILTER (WHERE error_category IS NOT NULL) as error_counts,
            AVG(retry_count) as avg_retries,
            MAX(retry_count) as max_retries
        FROM form_submissions
        WHERE
            user_id = $1
            AND created_at >= start_date
            AND is_deleted = false
    )
    SELECT jsonb_build_object(
        'total_submissions', total_submissions,
        'status_counts', status_counts,
        'avg_processing_time_ms', avg_processing_time_ms,
        'error_counts', error_counts,
        'retry_metrics', jsonb_build_object(
            'avg_retries', avg_retries,
            'max_retries', max_retries
        )
    ) INTO result
    FROM metrics;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get submission timeline
CREATE OR REPLACE FUNCTION get_submission_timeline(
    user_id UUID,
    days INTEGER DEFAULT 30
) RETURNS JSONB AS $$
DECLARE
    start_date TIMESTAMP WITH TIME ZONE;
    result JSONB;
BEGIN
    start_date := NOW() - (days || ' days')::INTERVAL;
    
    WITH timeline AS (
        SELECT jsonb_agg(
            jsonb_build_object(
                'timestamp', created_at,
                'type', 'submission_created',
                'submission_id', id,
                'status', status
            )
        ) as creation_events,
        jsonb_agg(
            jsonb_build_object(
                'timestamp', processing_completed_at,
                'type', 'submission_completed',
                'submission_id', id,
                'status', status,
                'duration_ms', processing_duration_ms
            )
        ) FILTER (WHERE processing_completed_at IS NOT NULL) as completion_events,
        jsonb_agg(events) as status_events
        FROM form_submissions
        WHERE
            user_id = $1
            AND created_at >= start_date
            AND is_deleted = false
    )
    SELECT jsonb_build_object(
        'timeline', (
            SELECT jsonb_agg(event ORDER BY (event->>'timestamp')::TIMESTAMP WITH TIME ZONE DESC)
            FROM (
                SELECT jsonb_array_elements(creation_events) as event
                FROM timeline
                UNION ALL
                SELECT jsonb_array_elements(completion_events) as event
                FROM timeline
                UNION ALL
                SELECT jsonb_array_elements(status_events) as event
                FROM timeline
            ) events
        )
    ) INTO result
    FROM timeline;
    
    RETURN result->'timeline';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get error analytics
CREATE OR REPLACE FUNCTION get_error_analytics(
    user_id UUID,
    days INTEGER DEFAULT 30
) RETURNS JSONB AS $$
DECLARE
    start_date TIMESTAMP WITH TIME ZONE;
    result JSONB;
BEGIN
    start_date := NOW() - (days || ' days')::INTERVAL;
    
    WITH error_details AS (
        SELECT jsonb_agg(
            jsonb_build_object(
                'timestamp', created_at,
                'submission_id', id,
                'category', error_category,
                'code', error_code,
                'message', error_message,
                'details', error_details
            )
            ORDER BY created_at DESC
        ) as details,
        jsonb_agg(
            jsonb_build_object(
                'date', DATE_TRUNC('day', created_at),
                'category', error_category,
                'count', COUNT(*)
            )
            ORDER BY DATE_TRUNC('day', created_at) DESC, error_category
        ) as trends
        FROM form_submissions
        WHERE
            user_id = $1
            AND created_at >= start_date
            AND is_deleted = false
            AND error_category IS NOT NULL
        GROUP BY DATE_TRUNC('day', created_at), error_category
    )
    SELECT jsonb_build_object(
        'error_details', details,
        'error_trends', trends
    ) INTO result
    FROM error_details;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 