-- Drop existing tables if they exist (in reverse order of dependencies)
DROP TABLE IF EXISTS public.submission_notifications CASCADE;
DROP TABLE IF EXISTS public.submission_timeline CASCADE;
DROP TABLE IF EXISTS public.pdf_documents CASCADE;
DROP TABLE IF EXISTS public.field_mappings CASCADE;
DROP TABLE IF EXISTS public.form_submissions CASCADE;
DROP TABLE IF EXISTS public.form_templates CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;

-- Drop existing views and functions
DROP VIEW IF EXISTS public.submission_status_view CASCADE;
DROP FUNCTION IF EXISTS public.update_submission_status CASCADE;

-- Create users table
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

-- Create form_templates table
CREATE TABLE public.form_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    fields JSONB NOT NULL,
    validation_rules JSONB,
    user_id UUID REFERENCES public.users(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

-- Create form_submissions table
CREATE TABLE public.form_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID REFERENCES public.form_templates(id),
    user_id UUID REFERENCES public.users(id),
    data JSONB NOT NULL,
    status VARCHAR(50) NOT NULL,
    error_category VARCHAR(50),
    error_details JSONB,
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    processing_duration_ms INTEGER,
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

-- Create submission_timeline table
CREATE TABLE public.submission_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID REFERENCES public.form_submissions(id),
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES public.users(id)
);

-- Create submission_notifications table
CREATE TABLE public.submission_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID REFERENCES public.form_submissions(id),
    notification_type VARCHAR(50) NOT NULL,
    notification_data JSONB,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

-- Create field_mappings table
CREATE TABLE public.field_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID REFERENCES public.form_templates(id),
    source_field VARCHAR(255) NOT NULL,
    target_field VARCHAR(255) NOT NULL,
    transformation_rules JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

-- Create pdf_documents table
CREATE TABLE public.pdf_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id),
    filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    storage_path VARCHAR(512) NOT NULL,
    extracted_data JSONB,
    processing_status VARCHAR(50) NOT NULL,
    error_details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

-- Create submission_status_view
CREATE VIEW public.submission_status_view AS
SELECT 
    fs.id,
    fs.status,
    fs.error_category,
    fs.processing_started_at,
    fs.processing_completed_at,
    fs.processing_duration_ms,
    fs.retry_count,
    fs.next_retry_at,
    ft.name as template_name,
    u.email as user_email
FROM public.form_submissions fs
JOIN public.form_templates ft ON fs.template_id = ft.id
JOIN public.users u ON fs.user_id = u.id;

-- Create update_submission_status function
CREATE OR REPLACE FUNCTION public.update_submission_status(
    submission_id UUID,
    new_status TEXT,
    error_category TEXT DEFAULT NULL
) RETURNS void AS $$
BEGIN
    UPDATE public.form_submissions
    SET 
        status = new_status,
        error_category = error_category,
        updated_at = now()
    WHERE id = submission_id;
    
    INSERT INTO public.submission_timeline (
        submission_id,
        event_type,
        event_data
    ) VALUES (
        submission_id,
        'status_change',
        jsonb_build_object(
            'old_status', (SELECT status FROM public.form_submissions WHERE id = submission_id),
            'new_status', new_status,
            'error_category', error_category
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Enable Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.form_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.form_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.field_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pdf_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submission_timeline ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submission_notifications ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own data" ON public.users;
DROP POLICY IF EXISTS "Users can view their own form templates" ON public.form_templates;
DROP POLICY IF EXISTS "Users can view their own form submissions" ON public.form_submissions;
DROP POLICY IF EXISTS "Users can view their own field mappings" ON public.field_mappings;
DROP POLICY IF EXISTS "Users can view their own PDF documents" ON public.pdf_documents;
DROP POLICY IF EXISTS "Users can view timeline of their submissions" ON public.submission_timeline;
DROP POLICY IF EXISTS "Users can create timeline events for their submissions" ON public.submission_timeline;
DROP POLICY IF EXISTS "Users can view their own notifications" ON public.submission_notifications;

-- Create RLS policies
CREATE POLICY "Users can view their own data" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can view their own form templates" ON public.form_templates
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own form submissions" ON public.form_submissions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own field mappings" ON public.field_mappings
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM public.form_templates
        WHERE form_templates.id = field_mappings.template_id
        AND form_templates.user_id = auth.uid()
    ));

CREATE POLICY "Users can view their own PDF documents" ON public.pdf_documents
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view timeline of their submissions" ON public.submission_timeline
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM public.form_submissions
        WHERE form_submissions.id = submission_timeline.submission_id
        AND form_submissions.user_id = auth.uid()
    ));

CREATE POLICY "Users can create timeline events for their submissions" ON public.submission_timeline
    FOR INSERT WITH CHECK (EXISTS (
        SELECT 1 FROM public.form_submissions
        WHERE form_submissions.id = submission_timeline.submission_id
        AND form_submissions.user_id = auth.uid()
    ));

CREATE POLICY "Users can view their own notifications" ON public.submission_notifications
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM public.form_submissions
        WHERE form_submissions.id = submission_notifications.submission_id
        AND form_submissions.user_id = auth.uid()
    ));

-- Create indexes
CREATE INDEX ix_users_email ON public.users(email);
CREATE INDEX ix_form_templates_user_id ON public.form_templates(user_id);
CREATE INDEX ix_form_submissions_template_id ON public.form_submissions(template_id);
CREATE INDEX ix_form_submissions_user_id ON public.form_submissions(user_id);
CREATE INDEX ix_form_submissions_status ON public.form_submissions(status);
CREATE INDEX ix_field_mappings_template_id ON public.field_mappings(template_id);
CREATE INDEX ix_pdf_documents_user_id ON public.pdf_documents(user_id);
CREATE INDEX ix_submission_timeline_submission_id ON public.submission_timeline(submission_id);
CREATE INDEX ix_submission_notifications_submission_id ON public.submission_notifications(submission_id);
CREATE INDEX ix_submission_notifications_is_read ON public.submission_notifications(is_read); 