-- Create submissions table and its indexes
DO $$
BEGIN
    -- Create the table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'submissions'
    ) THEN
        CREATE TABLE submissions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
            form_id TEXT NOT NULL,
            form_data JSONB DEFAULT '{}',
            screenshots JSONB DEFAULT '{}',
            status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'submitted', 'processing', 'completed', 'failed')),
            message TEXT,
            events JSONB[] DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            confirmation_number TEXT,
            error TEXT,
            metadata JSONB DEFAULT '{}',
            document_id UUID,
            response_data JSONB DEFAULT '{}'
        );

        -- Create indexes immediately after table creation
        CREATE INDEX idx_submissions_user_id ON submissions(user_id);
        CREATE INDEX idx_submissions_form_id ON submissions(form_id);
        CREATE INDEX idx_submissions_status ON submissions(status);
        CREATE INDEX idx_submissions_created_at ON submissions(created_at);
        CREATE INDEX idx_submissions_document_id ON submissions(document_id);
        CREATE INDEX idx_submissions_metadata ON submissions USING GIN (metadata);

        -- Enable RLS
        ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;

        -- Create policies
        CREATE POLICY "Users can view their own submissions" 
            ON submissions 
            FOR SELECT 
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can create their own submissions" 
            ON submissions 
            FOR INSERT 
            WITH CHECK (auth.uid() = user_id);

        CREATE POLICY "Users can update their own submissions" 
            ON submissions 
            FOR UPDATE 
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can delete their own submissions" 
            ON submissions 
            FOR DELETE 
            USING (auth.uid() = user_id);

        -- Create trigger
        CREATE TRIGGER set_submissions_updated_at
            BEFORE UPDATE ON submissions
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Create task_runs table and its indexes
DO $$
BEGIN
    -- Create the table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'task_runs'
    ) THEN
        CREATE TABLE task_runs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
            task_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'retrying')),
            current_step TEXT,
            progress FLOAT DEFAULT 0.0,
            input_data JSONB DEFAULT '{}',
            output_data JSONB DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            error_message TEXT,
            error_details JSONB,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE
        );

        -- Create indexes immediately after table creation
        CREATE INDEX idx_task_runs_user_id ON task_runs(user_id);
        CREATE INDEX idx_task_runs_task_type ON task_runs(task_type);
        CREATE INDEX idx_task_runs_status ON task_runs(status);
        CREATE INDEX idx_task_runs_created_at ON task_runs(created_at);
        CREATE INDEX idx_task_runs_metadata ON task_runs USING GIN (metadata);

        -- Enable RLS
        ALTER TABLE task_runs ENABLE ROW LEVEL SECURITY;

        -- Create policies
        CREATE POLICY "Users can view their own tasks" 
            ON task_runs 
            FOR SELECT 
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can create their own tasks" 
            ON task_runs 
            FOR INSERT 
            WITH CHECK (auth.uid() = user_id);

        CREATE POLICY "Users can update their own tasks" 
            ON task_runs 
            FOR UPDATE 
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can delete their own tasks" 
            ON task_runs 
            FOR DELETE 
            USING (auth.uid() = user_id);

        -- Create trigger
        CREATE TRIGGER set_task_runs_updated_at
            BEFORE UPDATE ON task_runs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$; 