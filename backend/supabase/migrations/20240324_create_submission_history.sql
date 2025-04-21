-- Create submission_history table and its indexes
DO $$
BEGIN
    -- Create the table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'submission_history'
    ) THEN
        CREATE TABLE submission_history (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            submission_id UUID REFERENCES submissions(id) ON DELETE CASCADE,
            status TEXT NOT NULL,
            message TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        );

        -- Create indexes immediately after table creation
        CREATE INDEX idx_submission_history_submission_id ON submission_history(submission_id);
        CREATE INDEX idx_submission_history_status ON submission_history(status);
        CREATE INDEX idx_submission_history_created_at ON submission_history(created_at);
        CREATE INDEX idx_submission_history_metadata ON submission_history USING GIN (metadata);

        -- Enable RLS
        ALTER TABLE submission_history ENABLE ROW LEVEL SECURITY;

        -- Create policies
        CREATE POLICY "Users can view their own submission history" 
            ON submission_history 
            FOR SELECT 
            USING (
                EXISTS (
                    SELECT 1 FROM submissions 
                    WHERE submissions.id = submission_history.submission_id 
                    AND submissions.user_id = auth.uid()
                )
            );

        CREATE POLICY "Users can create their own submission history" 
            ON submission_history 
            FOR INSERT 
            WITH CHECK (
                EXISTS (
                    SELECT 1 FROM submissions 
                    WHERE submissions.id = submission_history.submission_id 
                    AND submissions.user_id = auth.uid()
                )
            );

        CREATE POLICY "Users can update their own submission history" 
            ON submission_history 
            FOR UPDATE 
            USING (
                EXISTS (
                    SELECT 1 FROM submissions 
                    WHERE submissions.id = submission_history.submission_id 
                    AND submissions.user_id = auth.uid()
                )
            );

        CREATE POLICY "Users can delete their own submission history" 
            ON submission_history 
            FOR DELETE 
            USING (
                EXISTS (
                    SELECT 1 FROM submissions 
                    WHERE submissions.id = submission_history.submission_id 
                    AND submissions.user_id = auth.uid()
                )
            );
    END IF;
END
$$; 