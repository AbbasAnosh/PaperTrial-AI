-- ML-related tables
CREATE TABLE IF NOT EXISTS ml_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50),
    description TEXT,
    model_type VARCHAR(100),
    parameters JSONB,
    metrics JSONB,
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES auth.users(id),
    model_path TEXT,
    is_active BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS ml_model_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES ml_models(id) ON DELETE CASCADE,
    metrics JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ml_model_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES ml_models(id) ON DELETE CASCADE,
    evaluation_data JSONB,
    metrics JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    evaluator UUID REFERENCES auth.users(id),
    status VARCHAR(50),
    notes TEXT,
    version VARCHAR(50),
    dataset_id UUID
);

CREATE TABLE IF NOT EXISTS ml_inference_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES ml_models(id) ON DELETE CASCADE,
    inference_time FLOAT,
    confidence_score FLOAT,
    accuracy FLOAT,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ml_system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100),
    metric_value JSONB
);

CREATE TABLE IF NOT EXISTS ml_training_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    data_type VARCHAR(50),
    content JSONB,
    labels JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES auth.users(id),
    version VARCHAR(50)
);

-- Form-related tables
CREATE TABLE IF NOT EXISTS form_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    fields JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES auth.users(id),
    version VARCHAR(50),
    status VARCHAR(50),
    category VARCHAR(100),
    metadata JSONB,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS form_fields (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES form_templates(id) ON DELETE CASCADE,
    field_name VARCHAR(255),
    field_type VARCHAR(100),
    is_required BOOLEAN DEFAULT false,
    validation_rules JSONB,
    default_value TEXT,
    order_index INTEGER
);

CREATE TABLE IF NOT EXISTS form_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    form_id UUID,
    user_id UUID REFERENCES auth.users(id),
    status VARCHAR(50),
    progress FLOAT,
    completed_at TIMESTAMP WITH TIME ZONE,
    last_modified TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Form submissions table
CREATE TABLE IF NOT EXISTS form_submissions (
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

-- Workspace-related tables
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES auth.users(id),
    settings JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(50),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50),
    permissions JSONB,
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE IF NOT EXISTS workspace_invites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    email VARCHAR(255),
    role VARCHAR(50),
    status VARCHAR(50),
    invited_by UUID REFERENCES auth.users(id),
    invited_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    token VARCHAR(255)
);

-- Other tables
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255),
    content_type VARCHAR(100),
    size BIGINT,
    storage_path TEXT,
    uploaded_by UUID REFERENCES auth.users(id),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    workspace_id UUID REFERENCES workspaces(id),
    metadata JSONB,
    status VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS annotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    content TEXT,
    annotation_type VARCHAR(100),
    position JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    status VARCHAR(50),
    parent_id UUID REFERENCES annotations(id),
    version INTEGER DEFAULT 1,
    is_resolved BOOLEAN DEFAULT false,
    resolved_by UUID REFERENCES auth.users(id)
);

CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT,
    user_id UUID REFERENCES auth.users(id),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    parent_id UUID REFERENCES comments(id),
    status VARCHAR(50),
    metadata JSONB,
    is_edited BOOLEAN DEFAULT false,
    edited_at TIMESTAMP WITH TIME ZONE,
    position JSONB
);

CREATE TABLE IF NOT EXISTS field_mapping_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_field VARCHAR(255),
    target_field VARCHAR(255),
    transformation_rule JSONB,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    priority INTEGER,
    conditions JSONB,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS field_mapping_corrections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID REFERENCES field_mapping_rules(id) ON DELETE CASCADE,
    original_value TEXT,
    corrected_value TEXT,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    confidence_score FLOAT,
    status VARCHAR(50),
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS field_mapping_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_field VARCHAR(255),
    target_field VARCHAR(255),
    confidence_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50),
    metadata JSONB,
    suggested_by VARCHAR(100),
    feedback JSONB
);

-- Add RLS policies for all tables
DO $$
DECLARE
    table_name text;
BEGIN
    FOR table_name IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public')
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', table_name);
        
        -- Basic select policy
        EXECUTE format(
            'CREATE POLICY "Users can view their own data" ON %I
             FOR SELECT USING (auth.uid() IN (
                SELECT user_id FROM workspace_members wm
                WHERE wm.workspace_id = %I.workspace_id
             ));',
            table_name,
            table_name
        );
        
        -- Basic insert policy
        EXECUTE format(
            'CREATE POLICY "Users can insert their own data" ON %I
             FOR INSERT WITH CHECK (auth.uid() IN (
                SELECT user_id FROM workspace_members wm
                WHERE wm.workspace_id = %I.workspace_id
             ));',
            table_name,
            table_name
        );
        
        -- Basic update policy
        EXECUTE format(
            'CREATE POLICY "Users can update their own data" ON %I
             FOR UPDATE USING (auth.uid() IN (
                SELECT user_id FROM workspace_members wm
                WHERE wm.workspace_id = %I.workspace_id
             ));',
            table_name,
            table_name
        );
        
        -- Basic delete policy
        EXECUTE format(
            'CREATE POLICY "Users can delete their own data" ON %I
             FOR DELETE USING (auth.uid() IN (
                SELECT user_id FROM workspace_members wm
                WHERE wm.workspace_id = %I.workspace_id
             ));',
            table_name,
            table_name
        );
    END LOOP;
END
$$;

-- Add RLS policies for form_submissions
ALTER TABLE form_submissions ENABLE ROW LEVEL SECURITY;

-- Users can only view their own submissions
CREATE POLICY "Users can view their own submissions" 
    ON form_submissions 
    FOR SELECT 
    USING (auth.uid() = user_id);

-- Users can only create their own submissions
CREATE POLICY "Users can create their own submissions" 
    ON form_submissions 
    FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- Users can only update their own submissions
CREATE POLICY "Users can update their own submissions" 
    ON form_submissions 
    FOR UPDATE 
    USING (auth.uid() = user_id);

-- Users can only delete their own submissions
CREATE POLICY "Users can delete their own submissions" 
    ON form_submissions 
    FOR DELETE 
    USING (auth.uid() = user_id);

-- Add trigger for updated_at
CREATE TRIGGER set_form_submissions_updated_at
    BEFORE UPDATE ON form_submissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for form_submissions
CREATE INDEX IF NOT EXISTS idx_form_submissions_user_id ON form_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_form_id ON form_submissions(form_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_status ON form_submissions(status);
CREATE INDEX IF NOT EXISTS idx_form_submissions_created_at ON form_submissions(created_at);
CREATE INDEX IF NOT EXISTS idx_form_submissions_events ON form_submissions USING GIN (events);
CREATE INDEX IF NOT EXISTS idx_form_submissions_metadata ON form_submissions USING GIN (metadata); 