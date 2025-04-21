-- Drop existing objects if they exist
DROP TRIGGER IF EXISTS update_annotations_updated_at ON annotations;
DROP TRIGGER IF EXISTS update_comments_updated_at ON comments;
DROP INDEX IF EXISTS idx_annotations_workspace_id;
DROP INDEX IF EXISTS idx_annotations_file_id;
DROP INDEX IF EXISTS idx_annotations_user_id;
DROP INDEX IF EXISTS idx_annotations_status;
DROP INDEX IF EXISTS idx_annotations_created_at;
DROP INDEX IF EXISTS idx_comments_workspace_id;
DROP INDEX IF EXISTS idx_comments_file_id;
DROP INDEX IF EXISTS idx_comments_user_id;
DROP INDEX IF EXISTS idx_comments_parent_id;
DROP INDEX IF EXISTS idx_comments_is_resolved;
DROP INDEX IF EXISTS idx_comments_created_at;
DROP POLICY IF EXISTS "Users can view annotations in their workspaces" ON annotations;
DROP POLICY IF EXISTS "Users can create annotations in their workspaces" ON annotations;
DROP POLICY IF EXISTS "Users can update their own annotations" ON annotations;
DROP POLICY IF EXISTS "Users can delete their own annotations" ON annotations;
DROP POLICY IF EXISTS "Users can view comments in their workspaces" ON comments;
DROP POLICY IF EXISTS "Users can create comments in their workspaces" ON comments;
DROP POLICY IF EXISTS "Users can update their own comments" ON comments;
DROP POLICY IF EXISTS "Users can delete their own comments" ON comments;

-- Create enum types for annotation and comment status if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'annotation_type') THEN
        CREATE TYPE annotation_type AS ENUM (
            'comment',
            'highlight',
            'signature',
            'approval',
            'rejection',
            'suggestion'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'annotation_status') THEN
        CREATE TYPE annotation_status AS ENUM (
            'pending',
            'resolved',
            'rejected',
            'approved'
        );
    END IF;
END $$;

-- Create annotations table
CREATE TABLE IF NOT EXISTS annotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    file_id UUID NOT NULL,
    user_id UUID NOT NULL,
    type annotation_type NOT NULL,
    status annotation_status NOT NULL DEFAULT 'pending',
    content TEXT NOT NULL,
    position JSONB NOT NULL,
    page_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID,
    metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT fk_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_resolved_by FOREIGN KEY (resolved_by) REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Create comments table
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    file_id UUID NOT NULL,
    user_id UUID NOT NULL,
    parent_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID,
    metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT fk_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_resolved_by FOREIGN KEY (resolved_by) REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_annotations_workspace_id ON annotations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_annotations_file_id ON annotations(file_id);
CREATE INDEX IF NOT EXISTS idx_annotations_user_id ON annotations(user_id);
CREATE INDEX IF NOT EXISTS idx_annotations_status ON annotations(status);
CREATE INDEX IF NOT EXISTS idx_annotations_created_at ON annotations(created_at);

CREATE INDEX IF NOT EXISTS idx_comments_workspace_id ON comments(workspace_id);
CREATE INDEX IF NOT EXISTS idx_comments_file_id ON comments(file_id);
CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments(parent_id);
CREATE INDEX IF NOT EXISTS idx_comments_is_resolved ON comments(is_resolved);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);

-- Create RLS policies for annotations
ALTER TABLE annotations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view annotations in their workspaces"
    ON annotations FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = annotations.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create annotations in their workspaces"
    ON annotations FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = annotations.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update their own annotations"
    ON annotations FOR UPDATE
    USING (
        user_id = auth.uid()
        AND EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = annotations.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete their own annotations"
    ON annotations FOR DELETE
    USING (
        user_id = auth.uid()
        AND EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = annotations.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );

-- Create RLS policies for comments
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view comments in their workspaces"
    ON comments FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = comments.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create comments in their workspaces"
    ON comments FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = comments.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update their own comments"
    ON comments FOR UPDATE
    USING (
        user_id = auth.uid()
        AND EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = comments.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete their own comments"
    ON comments FOR DELETE
    USING (
        user_id = auth.uid()
        AND EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = comments.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );

-- Create functions to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updating timestamps
CREATE TRIGGER update_annotations_updated_at
    BEFORE UPDATE ON annotations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_comments_updated_at
    BEFORE UPDATE ON comments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 