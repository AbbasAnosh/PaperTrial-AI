-- Add webhook support

-- Create webhooks table
CREATE TABLE IF NOT EXISTS webhooks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    url TEXT NOT NULL,
    events TEXT[] NOT NULL,
    secret TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster webhook queries
CREATE INDEX IF NOT EXISTS idx_webhooks_user_id 
ON webhooks(user_id);

-- Create webhook_deliveries table to track webhook delivery attempts
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    webhook_id UUID REFERENCES webhooks(id) NOT NULL,
    event TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL,
    response_code INTEGER,
    response_body TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster webhook delivery queries
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_webhook_id 
ON webhook_deliveries(webhook_id);

-- Create index for faster webhook delivery status queries
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status 
ON webhook_deliveries(status);

-- Add RLS policies
ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY;

-- Users can only view their own webhooks
CREATE POLICY "Users can view their own webhooks"
    ON webhooks
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- Users can only insert their own webhooks
CREATE POLICY "Users can insert their own webhooks"
    ON webhooks
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- Users can only update their own webhooks
CREATE POLICY "Users can update their own webhooks"
    ON webhooks
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can only delete their own webhooks
CREATE POLICY "Users can delete their own webhooks"
    ON webhooks
    FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Users can only view their own webhook deliveries
CREATE POLICY "Users can view their own webhook deliveries"
    ON webhook_deliveries
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM webhooks
            WHERE webhooks.id = webhook_deliveries.webhook_id
            AND webhooks.user_id = auth.uid()
        )
    );

-- Create function to log webhook delivery
CREATE OR REPLACE FUNCTION log_webhook_delivery(
    p_webhook_id UUID,
    p_event TEXT,
    p_payload JSONB,
    p_status TEXT,
    p_response_code INTEGER DEFAULT NULL,
    p_response_body TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_delivery_id UUID;
BEGIN
    INSERT INTO webhook_deliveries (
        webhook_id,
        event,
        payload,
        status,
        response_code,
        response_body
    )
    VALUES (
        p_webhook_id,
        p_event,
        p_payload,
        p_status,
        p_response_code,
        p_response_body
    )
    RETURNING id INTO v_delivery_id;
    
    RETURN v_delivery_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant necessary permissions
GRANT ALL ON webhooks TO authenticated;
GRANT ALL ON webhook_deliveries TO authenticated;
GRANT EXECUTE ON FUNCTION log_webhook_delivery(UUID, TEXT, JSONB, TEXT, INTEGER, TEXT) TO authenticated; 