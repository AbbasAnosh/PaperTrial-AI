-- Create field_mapping_rules table
CREATE TABLE IF NOT EXISTS field_mapping_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    source_field TEXT NOT NULL,
    target_field TEXT NOT NULL,
    rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN ('direct', 'transform', 'conditional')),
    rule_config JSONB NOT NULL,
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    UNIQUE(workspace_id, source_field, target_field)
);

-- Create field_mapping_corrections table
CREATE TABLE IF NOT EXISTS field_mapping_corrections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES field_mapping_rules(id) ON DELETE CASCADE,
    original_value TEXT NOT NULL,
    corrected_value TEXT NOT NULL,
    context JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NOT NULL REFERENCES auth.users(id)
);

-- Create field_mapping_suggestions table
CREATE TABLE IF NOT EXISTS field_mapping_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    source_field TEXT NOT NULL,
    suggested_field TEXT NOT NULL,
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    context JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NOT NULL REFERENCES auth.users(id)
);

-- Create indexes for field_mapping_rules
CREATE INDEX idx_field_mapping_rules_workspace ON field_mapping_rules(workspace_id);
CREATE INDEX idx_field_mapping_rules_source_field ON field_mapping_rules(source_field);
CREATE INDEX idx_field_mapping_rules_target_field ON field_mapping_rules(target_field);
CREATE INDEX idx_field_mapping_rules_is_active ON field_mapping_rules(is_active);

-- Create indexes for field_mapping_corrections
CREATE INDEX idx_field_mapping_corrections_workspace ON field_mapping_corrections(workspace_id);
CREATE INDEX idx_field_mapping_corrections_rule ON field_mapping_corrections(rule_id);
CREATE INDEX idx_field_mapping_corrections_created_at ON field_mapping_corrections(created_at);

-- Create indexes for field_mapping_suggestions
CREATE INDEX idx_field_mapping_suggestions_workspace ON field_mapping_suggestions(workspace_id);
CREATE INDEX idx_field_mapping_suggestions_source_field ON field_mapping_suggestions(source_field);
CREATE INDEX idx_field_mapping_suggestions_confidence ON field_mapping_suggestions(confidence_score);

-- Add RLS policies for field_mapping_rules
ALTER TABLE field_mapping_rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their workspace's mapping rules"
    ON field_mapping_rules FOR SELECT
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
    ));

CREATE POLICY "Users can create mapping rules in their workspace"
    ON field_mapping_rules FOR INSERT
    WITH CHECK (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
        AND role IN ('owner', 'admin')
    ));

-- Add RLS policies for field_mapping_corrections
ALTER TABLE field_mapping_corrections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their workspace's mapping corrections"
    ON field_mapping_corrections FOR SELECT
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
    ));

CREATE POLICY "Users can create mapping corrections in their workspace"
    ON field_mapping_corrections FOR INSERT
    WITH CHECK (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
    ));

-- Add RLS policies for field_mapping_suggestions
ALTER TABLE field_mapping_suggestions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their workspace's mapping suggestions"
    ON field_mapping_suggestions FOR SELECT
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
    ));

CREATE POLICY "Users can create mapping suggestions in their workspace"
    ON field_mapping_suggestions FOR INSERT
    WITH CHECK (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
    ));

-- Create triggers for updating timestamps
CREATE TRIGGER update_field_mapping_rules_updated_at
    BEFORE UPDATE ON field_mapping_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 