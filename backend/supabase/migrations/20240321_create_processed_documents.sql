-- Create processed_documents table
CREATE TABLE IF NOT EXISTS processed_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_filename TEXT NOT NULL,
    processed_data JSONB NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    form_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for better query performance
CREATE INDEX idx_processed_documents_user_id ON processed_documents(user_id);
CREATE INDEX idx_processed_documents_form_type ON processed_documents(form_type);
CREATE INDEX idx_processed_documents_status ON processed_documents(status);
CREATE INDEX idx_processed_documents_created_at ON processed_documents(created_at);
CREATE INDEX idx_processed_documents_metadata ON processed_documents USING GIN (metadata);

-- Add RLS policies
ALTER TABLE processed_documents ENABLE ROW LEVEL SECURITY;

-- Policy for users to view their own documents
CREATE POLICY "Users can view their own processed documents"
    ON processed_documents FOR SELECT
    USING (auth.uid() = user_id);

-- Policy for users to insert their own documents
CREATE POLICY "Users can insert their own processed documents"
    ON processed_documents FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy for users to update their own documents
CREATE POLICY "Users can update their own processed documents"
    ON processed_documents FOR UPDATE
    USING (auth.uid() = user_id);

-- Policy for users to delete their own documents
CREATE POLICY "Users can delete their own processed documents"
    ON processed_documents FOR DELETE
    USING (auth.uid() = user_id);

-- Create trigger for updating timestamps
CREATE TRIGGER update_processed_documents_updated_at
    BEFORE UPDATE ON processed_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 