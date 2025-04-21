-- Create workspace_invites table
CREATE TABLE IF NOT EXISTS workspace_invites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('owner', 'admin', 'member')),
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected', 'expired')),
    invited_by UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(workspace_id, email)
);

-- Create indexes for better query performance
CREATE INDEX idx_workspace_invites_workspace ON workspace_invites(workspace_id);
CREATE INDEX idx_workspace_invites_email ON workspace_invites(email);
CREATE INDEX idx_workspace_invites_status ON workspace_invites(status);
CREATE INDEX idx_workspace_invites_expires_at ON workspace_invites(expires_at);

-- Add RLS policies
ALTER TABLE workspace_invites ENABLE ROW LEVEL SECURITY;

-- Policy for users to view invites for their workspaces
CREATE POLICY "Users can view invites for their workspaces"
    ON workspace_invites FOR SELECT
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
        AND role IN ('owner', 'admin')
    ));

-- Policy for workspace owners and admins to create invites
CREATE POLICY "Workspace owners and admins can create invites"
    ON workspace_invites FOR INSERT
    WITH CHECK (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
        AND role IN ('owner', 'admin')
    ));

-- Policy for workspace owners and admins to update invites
CREATE POLICY "Workspace owners and admins can update invites"
    ON workspace_invites FOR UPDATE
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
        AND role IN ('owner', 'admin')
    ));

-- Policy for workspace owners and admins to delete invites
CREATE POLICY "Workspace owners and admins can delete invites"
    ON workspace_invites FOR DELETE
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid()
        AND role IN ('owner', 'admin')
    ));

-- Create trigger for updating timestamps
CREATE TRIGGER update_workspace_invites_updated_at
    BEFORE UPDATE ON workspace_invites
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 