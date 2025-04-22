# Task Queue Implementation

This directory contains the task queue implementation for the Paper Trail Automator.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install celery redis
```

### 2. Create a Celery Configuration File

Create a file named `celery_app.py` in the `backend/app` directory with the following content:

```python
from celery import Celery
import os

# Initialize Celery
celery_app = Celery('paper_trail_automator',
                   broker=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
                   backend=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['app.tasks'])
```

### 3. Create Task Files

Create the following files in the `backend/app/tasks` directory:

#### `__init__.py`

```python
# Empty file to make the directory a package
```

#### `form_processing.py`

```python
from app.celery_app import celery_app
from app.services.form_service_enhanced import EnhancedFormService
from app.models.form_submission import FormSubmission
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_form_submission(self, submission_id):
    """
    Process a form submission asynchronously.

    Args:
        submission_id: UUID of the form submission to process
    """
    try:
        logger.info(f"Starting to process submission {submission_id}")

        # Get the form service
        form_service = EnhancedFormService()

        # Process the submission
        result = form_service._process_submission(submission_id)

        logger.info(f"Successfully processed submission {submission_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing submission {submission_id}: {str(e)}")

        # Update submission status to failed
        try:
            form_service = EnhancedFormService()
            form_service.update_submission_status(
                submission_id=submission_id,
                new_status="failed",
                error_message=str(e),
                error_category="system",
                error_details={"exception": str(e), "traceback": self.request.traceback}
            )
        except Exception as update_error:
            logger.error(f"Failed to update submission status: {str(update_error)}")

        # Retry the task
        raise self.retry(exc=e)

@celery_app.task
def retry_failed_submissions():
    """
    Find failed submissions that need retrying and queue them for processing.
    """
    from app.models.form_submission import FormSubmission
    from app.services.form_service_enhanced import EnhancedFormService
    from datetime import datetime

    form_service = EnhancedFormService()

    # Get submissions that are failed and need retrying
    failed_submissions = FormSubmission.query.filter(
        FormSubmission.status == "failed",
        FormSubmission.retry_count < FormSubmission.max_retries,
        FormSubmission.next_retry_at <= datetime.utcnow()
    ).all()

    for submission in failed_submissions:
        # Queue the submission for processing
        process_form_submission.delay(submission.id)

        # Update the retry count
        submission.retry_count += 1
        submission.next_retry_at = None  # Will be set by the processing function
        submission.save()

    return len(failed_submissions)
```

### 4. Update the Form Service

Update the `create_submission` method in your form service to use the task queue:

```python
# Add to imports
from app.tasks.form_processing import process_form_submission

# Update the create_submission method
def create_submission(self, form_template_id, data, user_id):
    # ... existing code ...

    # Save the submission
    submission.save()

    # Queue the submission for processing
    process_form_submission.delay(submission.id)

    return submission
```

### 5. Set up a Celery Beat Schedule

Add the following to your `celery_app.py` file:

```python
# Add to the configuration
celery_app.conf.beat_schedule = {
    'retry-failed-submissions': {
        'task': 'app.tasks.form_processing.retry_failed_submissions',
        'schedule': 300.0,  # Run every 5 minutes
    },
}
```

### 6. Set up Redis

Install Redis or use a managed Redis service.

### 7. Start Celery Workers and Beat

```bash
# Start Celery worker
celery -A app.celery_app worker --loglevel=info

# Start Celery beat
celery -A app.celery_app beat --loglevel=info
```

## Integration with Supabase

If you're using Supabase, you might want to consider using Supabase Edge Functions instead of Celery. Here's how to set up a simple Edge Function for processing form submissions:

1. Create a new Edge Function in the Supabase dashboard
2. Use the following code:

```typescript
// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This enables autocomplete, go to definition, etc.

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // Create a Supabase client with the Auth context of the logged in user
    const supabaseClient = createClient(
      // Supabase API URL - env var exported by default.
      Deno.env.get("SUPABASE_URL") ?? "",
      // Supabase SERVICE_ROLE KEY - env var exported by default.
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "",
      // Create client with Auth context of the user that called the function.
      // This way your row-level-security (RLS) policies are applied.
      {
        global: {
          headers: { Authorization: req.headers.get("Authorization")! },
        },
      }
    );

    // Get the submission ID from the request
    const { submission_id } = await req.json();

    if (!submission_id) {
      return new Response(
        JSON.stringify({ error: "Submission ID is required" }),
        {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
          status: 400,
        }
      );
    }

    // Get the submission
    const { data: submission, error: submissionError } = await supabaseClient
      .from("form_submissions")
      .select("*")
      .eq("id", submission_id)
      .single();

    if (submissionError) {
      return new Response(JSON.stringify({ error: submissionError.message }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 500,
      });
    }

    // Get the form template
    const { data: formTemplate, error: templateError } = await supabaseClient
      .from("form_templates")
      .select("*")
      .eq("id", submission.form_template_id)
      .single();

    if (templateError) {
      return new Response(JSON.stringify({ error: templateError.message }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 500,
      });
    }

    // Update submission status to processing
    const { error: updateError } = await supabaseClient
      .from("form_submissions")
      .update({
        status: "processing",
        processing_started_at: new Date().toISOString(),
      })
      .eq("id", submission_id);

    if (updateError) {
      return new Response(JSON.stringify({ error: updateError.message }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 500,
      });
    }

    // Process the submission based on the template's submission method
    let result;
    try {
      if (formTemplate.submission_method === "HTTP_POST") {
        result = await processHttpPost(formTemplate, submission);
      } else if (formTemplate.submission_method === "API") {
        result = await processApi(formTemplate, submission);
      } else if (formTemplate.submission_method === "EMAIL") {
        result = await processEmail(formTemplate, submission);
      } else if (formTemplate.submission_method === "FILE") {
        result = await processFile(formTemplate, submission);
      } else if (formTemplate.submission_method === "CUSTOM") {
        result = await processCustom(formTemplate, submission);
      } else {
        throw new Error(
          `Unknown submission method: ${formTemplate.submission_method}`
        );
      }

      // Update submission status to completed
      const { error: completeError } = await supabaseClient
        .from("form_submissions")
        .update({
          status: "completed",
          processing_completed_at: new Date().toISOString(),
          processing_duration_ms: Math.floor(
            new Date().getTime() -
              new Date(submission.processing_started_at).getTime()
          ),
          response_data: result,
        })
        .eq("id", submission_id);

      if (completeError) {
        throw completeError;
      }

      return new Response(JSON.stringify({ result }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 200,
      });
    } catch (error) {
      // Update submission status to failed
      const { error: failError } = await supabaseClient
        .from("form_submissions")
        .update({
          status: "failed",
          processing_completed_at: new Date().toISOString(),
          processing_duration_ms: Math.floor(
            new Date().getTime() -
              new Date(submission.processing_started_at).getTime()
          ),
          error_message: error.message,
          error_category: categorizeError(error),
          error_details: {
            exception: error.message,
            traceback: error.stack,
          },
          next_retry_at:
            submission.retry_count < submission.max_retries
              ? new Date(
                  Date.now() +
                    submission.retry_backoff_seconds *
                      Math.pow(2, submission.retry_count) *
                      1000
                ).toISOString()
              : null,
        })
        .eq("id", submission_id);

      if (failError) {
        console.error("Failed to update submission status:", failError);
      }

      return new Response(JSON.stringify({ error: error.message }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 500,
      });
    }
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      status: 500,
    });
  }
});

// Helper functions for processing submissions
async function processHttpPost(formTemplate, submission) {
  // Implementation for HTTP POST submission
}

async function processApi(formTemplate, submission) {
  // Implementation for API submission
}

async function processEmail(formTemplate, submission) {
  // Implementation for email submission
}

async function processFile(formTemplate, submission) {
  // Implementation for file submission
}

async function processCustom(formTemplate, submission) {
  // Implementation for custom submission
}

function categorizeError(error) {
  if (error.name === "FetchError" || error.name === "NetworkError") {
    return "network";
  } else if (error.name === "ValidationError") {
    return "validation";
  } else if (error.name === "TimeoutError") {
    return "timeout";
  } else {
    return "system";
  }
}
```

3. Deploy the Edge Function
4. Update your form service to call the Edge Function instead of using Celery

## Next Steps

1. Implement the remaining submission methods in the `EnhancedFormService` class
2. Add rate limiting to prevent abuse
3. Create a field mapping UI for users to edit field matches
4. Implement analytics to track form processing metrics
5. Strengthen multi-user isolation with proper RLS policies
