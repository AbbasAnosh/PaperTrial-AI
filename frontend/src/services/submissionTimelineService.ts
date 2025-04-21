import { supabase } from "@/integrations/supabase/client";
import { FormSubmission } from "@/types/form";

export interface TimelineEvent {
  id: string;
  submissionId: string;
  eventType: "submission" | "status_update" | "error" | "completion";
  status: string;
  message: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export class SubmissionTimelineService {
  static async createTimelineEvent(
    submission: FormSubmission,
    eventType: TimelineEvent["eventType"],
    status: string,
    message: string,
    metadata?: Record<string, any>
  ): Promise<TimelineEvent> {
    const { data, error } = await supabase
      .from("submission_timeline")
      .insert({
        submission_id: submission.id,
        event_type: eventType,
        status,
        message,
        metadata,
        timestamp: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  static async getSubmissionTimeline(
    submissionId: string
  ): Promise<TimelineEvent[]> {
    const { data, error } = await supabase
      .from("submission_timeline")
      .select("*")
      .eq("submission_id", submissionId)
      .order("timestamp", { ascending: true });

    if (error) throw error;
    return data || [];
  }

  static async pollSubmissionStatus(
    submissionId: string
  ): Promise<TimelineEvent | null> {
    const { data, error } = await supabase
      .from("submission_timeline")
      .select("*")
      .eq("submission_id", submissionId)
      .order("timestamp", { ascending: false })
      .limit(1)
      .single();

    if (error) throw error;
    return data;
  }

  static async subscribeToStatusUpdates(
    submissionId: string,
    callback: (event: TimelineEvent) => void
  ) {
    const subscription = supabase
      .channel(`submission-${submissionId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "submission_timeline",
          filter: `submission_id=eq.${submissionId}`,
        },
        (payload) => {
          callback(payload.new as TimelineEvent);
        }
      )
      .subscribe();

    return () => {
      subscription.unsubscribe();
    };
  }
}
