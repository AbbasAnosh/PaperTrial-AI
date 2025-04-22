-- Add admin tables and functions

-- Create user_roles table
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, role)
);

-- Create admin_actions table
CREATE TABLE IF NOT EXISTS admin_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role);
CREATE INDEX IF NOT EXISTS idx_admin_actions_admin_id ON admin_actions(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_actions_entity ON admin_actions(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_admin_actions_created_at ON admin_actions(created_at);

-- Create function to check if user is admin
CREATE OR REPLACE FUNCTION is_admin(user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_roles.user_id = is_admin.user_id
        AND user_roles.role = 'admin'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to log admin action
CREATE OR REPLACE FUNCTION log_admin_action(
    admin_id UUID,
    action VARCHAR,
    entity_type VARCHAR,
    entity_id UUID,
    details JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    action_id UUID;
BEGIN
    -- Check if user is admin
    IF NOT is_admin(admin_id) THEN
        RAISE EXCEPTION 'User is not an admin';
    END IF;

    -- Insert action
    INSERT INTO admin_actions (
        admin_id,
        action,
        entity_type,
        entity_id,
        details
    ) VALUES (
        admin_id,
        action,
        entity_type,
        entity_id,
        details
    ) RETURNING id INTO action_id;

    RETURN action_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create RLS policies
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_actions ENABLE ROW LEVEL SECURITY;

-- User roles policies
CREATE POLICY "Users can view their own roles"
    ON user_roles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Only super admins can manage roles"
    ON user_roles FOR ALL
    USING (is_admin(auth.uid()))
    WITH CHECK (is_admin(auth.uid()));

-- Admin actions policies
CREATE POLICY "Admins can view all actions"
    ON admin_actions FOR SELECT
    USING (is_admin(auth.uid()));

CREATE POLICY "Admins can insert actions"
    ON admin_actions FOR INSERT
    WITH CHECK (is_admin(auth.uid()));

-- Grant permissions
GRANT SELECT ON user_roles TO authenticated;
GRANT ALL ON user_roles TO service_role;
GRANT SELECT ON admin_actions TO authenticated;
GRANT ALL ON admin_actions TO service_role;
GRANT EXECUTE ON FUNCTION is_admin TO authenticated;
GRANT EXECUTE ON FUNCTION log_admin_action TO authenticated; 