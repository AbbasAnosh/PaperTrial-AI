-- Create ML models table
CREATE TABLE IF NOT EXISTS ml_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    model_type VARCHAR(50) NOT NULL,
    storage_path TEXT NOT NULL,
    hyperparameters JSONB,
    metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NOT NULL REFERENCES users(id),
    is_active BOOLEAN DEFAULT true,
    UNIQUE(workspace_id, name, version)
);

-- Create ML training data table
CREATE TABLE IF NOT EXISTS ml_training_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    model_id UUID NOT NULL REFERENCES ml_models(id) ON DELETE CASCADE,
    source_field TEXT NOT NULL,
    target_field TEXT NOT NULL,
    document_type VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NOT NULL REFERENCES users(id)
);

-- Create ML model evaluations table
CREATE TABLE IF NOT EXISTS ml_model_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID NOT NULL REFERENCES ml_models(id) ON DELETE CASCADE,
    accuracy FLOAT NOT NULL,
    precision FLOAT NOT NULL,
    recall FLOAT NOT NULL,
    f1_score FLOAT NOT NULL,
    confusion_matrix JSONB NOT NULL,
    test_data_size INTEGER NOT NULL,
    evaluation_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NOT NULL REFERENCES users(id)
);

-- Create indexes for performance
CREATE INDEX idx_ml_models_workspace ON ml_models(workspace_id);
CREATE INDEX idx_ml_models_active ON ml_models(is_active);
CREATE INDEX idx_ml_training_data_workspace ON ml_training_data(workspace_id);
CREATE INDEX idx_ml_training_data_model ON ml_training_data(model_id);
CREATE INDEX idx_ml_model_evaluations_model ON ml_model_evaluations(model_id);

-- Create trigger for ml_models
CREATE TRIGGER update_ml_models_updated_at
    BEFORE UPDATE ON ml_models
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add RLS policies
ALTER TABLE ml_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_training_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_model_evaluations ENABLE ROW LEVEL SECURITY;

-- Policies for ml_models
CREATE POLICY "Users can view their workspace's models"
    ON ml_models FOR SELECT
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
    ));

CREATE POLICY "Users can create models in their workspace"
    ON ml_models FOR INSERT
    WITH CHECK (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
        AND role IN ('owner', 'admin')
    ));

-- Policies for ml_training_data
CREATE POLICY "Users can view their workspace's training data"
    ON ml_training_data FOR SELECT
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
    ));

CREATE POLICY "Users can add training data to their workspace"
    ON ml_training_data FOR INSERT
    WITH CHECK (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
        AND role IN ('owner', 'admin')
    ));

-- Policies for ml_model_evaluations
CREATE POLICY "Users can view their workspace's model evaluations"
    ON ml_model_evaluations FOR SELECT
    USING (model_id IN (
        SELECT id FROM ml_models
        WHERE workspace_id IN (
            SELECT workspace_id FROM workspace_members
            WHERE user_id = auth.uid()
        )
    ));

CREATE POLICY "Users can add evaluations to their workspace's models"
    ON ml_model_evaluations FOR INSERT
    WITH CHECK (model_id IN (
        SELECT id FROM ml_models
        WHERE workspace_id IN (
            SELECT workspace_id FROM workspace_members
            WHERE user_id = auth.uid()
            AND role IN ('owner', 'admin')
        )
    )); 