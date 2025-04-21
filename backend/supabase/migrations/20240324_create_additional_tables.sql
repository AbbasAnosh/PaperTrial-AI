-- Create file_metadata table and its indexes
DO $$
BEGIN
    -- Create the table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'file_metadata'
    ) THEN
        CREATE TABLE file_metadata (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            original_filename TEXT,
            file_type TEXT,
            file_path TEXT,
            size BIGINT,
            content_type TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        );

        -- Create indexes immediately after table creation
        CREATE INDEX idx_file_metadata_user_id ON file_metadata(user_id);
        CREATE INDEX idx_file_metadata_filename ON file_metadata(filename);
        CREATE INDEX idx_file_metadata_file_type ON file_metadata(file_type);
        CREATE INDEX idx_file_metadata_created_at ON file_metadata(created_at);
        CREATE INDEX idx_file_metadata_metadata ON file_metadata USING GIN (metadata);

        -- Enable RLS
        ALTER TABLE file_metadata ENABLE ROW LEVEL SECURITY;

        -- Create policies
        CREATE POLICY "Users can view their own file metadata" 
            ON file_metadata 
            FOR SELECT 
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can create their own file metadata" 
            ON file_metadata 
            FOR INSERT 
            WITH CHECK (auth.uid() = user_id);

        CREATE POLICY "Users can update their own file metadata" 
            ON file_metadata 
            FOR UPDATE 
            USING (auth.uid() = user_id);

        CREATE POLICY "Users can delete their own file metadata" 
            ON file_metadata 
            FOR DELETE 
            USING (auth.uid() = user_id);

        -- Create trigger
        CREATE TRIGGER set_file_metadata_updated_at
            BEFORE UPDATE ON file_metadata
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Create field_mapping_feedback table and its indexes
DO $$
BEGIN
    -- Create the table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'field_mapping_feedback'
    ) THEN
        CREATE TABLE field_mapping_feedback (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
            source_field TEXT NOT NULL,
            suggested_field TEXT NOT NULL,
            was_helpful BOOLEAN NOT NULL,
            feedback_text TEXT,
            created_by UUID REFERENCES auth.users(id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            metadata JSONB DEFAULT '{}'
        );

        -- Create indexes immediately after table creation
        CREATE INDEX idx_field_mapping_feedback_workspace ON field_mapping_feedback(workspace_id);
        CREATE INDEX idx_field_mapping_feedback_source_field ON field_mapping_feedback(source_field);
        CREATE INDEX idx_field_mapping_feedback_suggested_field ON field_mapping_feedback(suggested_field);
        CREATE INDEX idx_field_mapping_feedback_created_by ON field_mapping_feedback(created_by);
        CREATE INDEX idx_field_mapping_feedback_created_at ON field_mapping_feedback(created_at);
        CREATE INDEX idx_field_mapping_feedback_metadata ON field_mapping_feedback USING GIN (metadata);

        -- Enable RLS
        ALTER TABLE field_mapping_feedback ENABLE ROW LEVEL SECURITY;

        -- Create policies
        CREATE POLICY "Users can view feedback for their workspaces" 
            ON field_mapping_feedback 
            FOR SELECT 
            USING (
                EXISTS (
                    SELECT 1 FROM workspace_members 
                    WHERE workspace_members.workspace_id = field_mapping_feedback.workspace_id 
                    AND workspace_members.user_id = auth.uid()
                )
            );

        CREATE POLICY "Users can create feedback for their workspaces" 
            ON field_mapping_feedback 
            FOR INSERT 
            WITH CHECK (
                EXISTS (
                    SELECT 1 FROM workspace_members 
                    WHERE workspace_members.workspace_id = field_mapping_feedback.workspace_id 
                    AND workspace_members.user_id = auth.uid()
                )
            );

        CREATE POLICY "Users can update their own feedback" 
            ON field_mapping_feedback 
            FOR UPDATE 
            USING (created_by = auth.uid());

        CREATE POLICY "Users can delete their own feedback" 
            ON field_mapping_feedback 
            FOR DELETE 
            USING (created_by = auth.uid());
    END IF;
END
$$; 