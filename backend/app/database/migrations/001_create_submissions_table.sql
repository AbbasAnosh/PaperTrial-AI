CREATE TYPE submission_status AS ENUM ('queued', 'in_progress', 'completed', 'failed');

CREATE TABLE IF NOT EXISTS submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    form_id VARCHAR(255) NOT NULL,
    form_data JSONB NOT NULL,
    status submission_status NOT NULL DEFAULT 'queued',
    message TEXT,
    events JSONB[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_submissions_user_id ON submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status); 