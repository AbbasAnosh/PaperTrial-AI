
-- This is a reference schema file only. Tables should be created through SQL migrations.

-- Form progress table to track multi-step forms
CREATE TABLE IF NOT EXISTS form_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  form_id TEXT NOT NULL, -- e.g., 'ds160', 'i765', etc.
  form_data JSONB DEFAULT '{}', -- Stores the complete form data as JSON
  screenshots TEXT[] DEFAULT '{}', -- Array of screenshot references
  last_step_index INTEGER DEFAULT 0, -- Last completed step
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
  UNIQUE(user_id, form_id) -- One progress entry per user per form
);

-- Add RLS policies
ALTER TABLE form_progress ENABLE ROW LEVEL SECURITY;

-- Users can only see their own form progress
CREATE POLICY "Users can view their own form progress" 
  ON form_progress 
  FOR SELECT 
  USING (auth.uid() = user_id);

-- Users can only insert their own form progress  
CREATE POLICY "Users can create their own form progress" 
  ON form_progress 
  FOR INSERT 
  WITH CHECK (auth.uid() = user_id);
  
-- Users can only update their own form progress
CREATE POLICY "Users can update their own form progress" 
  ON form_progress 
  FOR UPDATE 
  USING (auth.uid() = user_id);

-- Users can only delete their own form progress
CREATE POLICY "Users can delete their own form progress" 
  ON form_progress 
  FOR DELETE 
  USING (auth.uid() = user_id);

-- Updated trigger function to keep updated_at current
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to form_progress table
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON form_progress
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
