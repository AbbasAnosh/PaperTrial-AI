-- Update ml_models table
ALTER TABLE ml_models
ADD COLUMN IF NOT EXISTS base_model VARCHAR(255),
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS parameters JSONB DEFAULT '{}'::jsonb;

-- Update ml_training_data table
ALTER TABLE ml_training_data
ADD COLUMN IF NOT EXISTS text TEXT,
ADD COLUMN IF NOT EXISTS labels TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Update field_mappings table
ALTER TABLE field_mappings
ADD COLUMN IF NOT EXISTS patterns TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS confidence_threshold FLOAT DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS validation_rules JSONB DEFAULT '{}'::jsonb;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_ml_models_base_model ON ml_models(base_model);
CREATE INDEX IF NOT EXISTS idx_ml_models_tags ON ml_models USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_ml_training_data_labels ON ml_training_data USING GIN (labels);
CREATE INDEX IF NOT EXISTS idx_field_mappings_patterns ON field_mappings USING GIN (patterns);
CREATE INDEX IF NOT EXISTS idx_field_mappings_confidence ON field_mappings(confidence_threshold);

-- Update RLS policies
ALTER TABLE ml_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_training_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE field_mappings ENABLE ROW LEVEL SECURITY;

-- Create policies for ml_models
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'ml_models' 
        AND policyname = 'Users can view their own models'
    ) THEN
        CREATE POLICY "Users can view their own models"
            ON ml_models FOR SELECT
            USING (auth.uid() = created_by);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'ml_models' 
        AND policyname = 'Users can create their own models'
    ) THEN
        CREATE POLICY "Users can create their own models"
            ON ml_models FOR INSERT
            WITH CHECK (auth.uid() = created_by);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'ml_models' 
        AND policyname = 'Users can update their own models'
    ) THEN
        CREATE POLICY "Users can update their own models"
            ON ml_models FOR UPDATE
            USING (auth.uid() = created_by);
    END IF;
END
$$;

-- Create policies for ml_training_data
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'ml_training_data' 
        AND policyname = 'Users can view their own training data'
    ) THEN
        CREATE POLICY "Users can view their own training data"
            ON ml_training_data FOR SELECT
            USING (auth.uid() = created_by);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'ml_training_data' 
        AND policyname = 'Users can create their own training data'
    ) THEN
        CREATE POLICY "Users can create their own training data"
            ON ml_training_data FOR INSERT
            WITH CHECK (auth.uid() = created_by);
    END IF;
END
$$;

-- Create policies for field_mappings
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'field_mappings' 
        AND policyname = 'Users can view their own field mappings'
    ) THEN
        CREATE POLICY "Users can view their own field mappings"
            ON field_mappings FOR SELECT
            USING (EXISTS (
                SELECT 1 FROM form_templates
                WHERE form_templates.id = field_mappings.template_id
                AND form_templates.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'field_mappings' 
        AND policyname = 'Users can create their own field mappings'
    ) THEN
        CREATE POLICY "Users can create their own field mappings"
            ON field_mappings FOR INSERT
            WITH CHECK (EXISTS (
                SELECT 1 FROM form_templates
                WHERE form_templates.id = field_mappings.template_id
                AND form_templates.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'field_mappings' 
        AND policyname = 'Users can update their own field mappings'
    ) THEN
        CREATE POLICY "Users can update their own field mappings"
            ON field_mappings FOR UPDATE
            USING (EXISTS (
                SELECT 1 FROM form_templates
                WHERE form_templates.id = field_mappings.template_id
                AND form_templates.user_id = auth.uid()
            ));
    END IF;
END
$$; 