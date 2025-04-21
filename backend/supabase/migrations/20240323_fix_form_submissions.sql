-- First, check if the table exists and create it if it doesn't
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'form_submissions'
    ) THEN
        -- Create the table if it doesn't exist
        CREATE TABLE form_submissions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
            form_id TEXT NOT NULL,
            form_data JSONB DEFAULT '{}',
            screenshots JSONB DEFAULT '{}',
            status submission_status DEFAULT 'queued',
            message TEXT,
            events JSONB[] DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            confirmation_number TEXT,
            error TEXT,
            metadata JSONB DEFAULT '{}'
        );
    END IF;
END
$$;

-- Enable RLS if not already enabled
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'form_submissions' 
        AND rowsecurity = true
    ) THEN
        ALTER TABLE form_submissions ENABLE ROW LEVEL SECURITY;
    END IF;
END
$$;

-- Create policies only if they don't exist
DO $$
BEGIN
    -- Check and create SELECT policy
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'form_submissions' 
        AND policyname = 'Users can view their own submissions'
    ) THEN
        CREATE POLICY "Users can view their own submissions" 
            ON form_submissions 
            FOR SELECT 
            USING (auth.uid() = user_id);
    END IF;

    -- Check and create INSERT policy
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'form_submissions' 
        AND policyname = 'Users can create their own submissions'
    ) THEN
        CREATE POLICY "Users can create their own submissions" 
            ON form_submissions 
            FOR INSERT 
            WITH CHECK (auth.uid() = user_id);
    END IF;

    -- Check and create UPDATE policy
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'form_submissions' 
        AND policyname = 'Users can update their own submissions'
    ) THEN
        CREATE POLICY "Users can update their own submissions" 
            ON form_submissions 
            FOR UPDATE 
            USING (auth.uid() = user_id);
    END IF;

    -- Check and create DELETE policy
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'form_submissions' 
        AND policyname = 'Users can delete their own submissions'
    ) THEN
        CREATE POLICY "Users can delete their own submissions" 
            ON form_submissions 
            FOR DELETE 
            USING (auth.uid() = user_id);
    END IF;
END
$$;

-- Create trigger if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'set_form_submissions_updated_at'
    ) THEN
        CREATE TRIGGER set_form_submissions_updated_at
            BEFORE UPDATE ON form_submissions
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Create basic indexes if they don't exist
DO $$
BEGIN
    -- Create index on user_id if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'form_submissions' 
        AND indexname = 'idx_form_submissions_user_id'
    ) THEN
        CREATE INDEX idx_form_submissions_user_id ON form_submissions(user_id);
    END IF;

    -- Create index on form_id if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'form_submissions' 
        AND indexname = 'idx_form_submissions_form_id'
    ) THEN
        CREATE INDEX idx_form_submissions_form_id ON form_submissions(form_id);
    END IF;

    -- Create index on status if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'form_submissions' 
        AND indexname = 'idx_form_submissions_status'
    ) THEN
        CREATE INDEX idx_form_submissions_status ON form_submissions(status);
    END IF;

    -- Create index on created_at if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'form_submissions' 
        AND indexname = 'idx_form_submissions_created_at'
    ) THEN
        CREATE INDEX idx_form_submissions_created_at ON form_submissions(created_at);
    END IF;

    -- Create GIN index on metadata if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'form_submissions' 
        AND indexname = 'idx_form_submissions_metadata'
    ) THEN
        CREATE INDEX idx_form_submissions_metadata ON form_submissions USING GIN (metadata);
    END IF;
END
$$;

-- Check if events column exists and create index if it does
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'form_submissions' 
        AND column_name = 'events'
    ) THEN
        -- Create index on events array length if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'form_submissions' 
            AND indexname = 'idx_form_submissions_events_length'
        ) THEN
            EXECUTE 'CREATE INDEX idx_form_submissions_events_length ON form_submissions(array_length(events, 1))';
        END IF;
    END IF;
END
$$; 