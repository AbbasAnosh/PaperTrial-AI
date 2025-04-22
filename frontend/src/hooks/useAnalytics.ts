import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/lib/supabase";

interface AnalyticsMetrics {
  total_submissions: number;
  status_counts: Record<string, number>;
  avg_processing_time_ms: number;
  error_counts: Record<string, number>;
  retry_metrics: {
    avg_retries: number;
    max_retries: number;
  };
}

interface TimelineEvent {
  timestamp: string;
  type: string;
  submission_id: string;
  status?: string;
  old_status?: string;
  new_status?: string;
  duration_ms?: number;
}

interface ErrorDetail {
  timestamp: string;
  submission_id: string;
  category: string;
  code: string;
  message: string;
  details: any;
}

interface ErrorAnalytics {
  error_details: ErrorDetail[];
  error_trends: {
    date: string;
    category: string;
    count: number;
  }[];
}

export function useAnalytics(days: number = 30) {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<AnalyticsMetrics>({
    total_submissions: 0,
    status_counts: {},
    avg_processing_time_ms: 0,
    error_counts: {},
    retry_metrics: {
      avg_retries: 0,
      max_retries: 0,
    },
  });
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [errorAnalytics, setErrorAnalytics] = useState<ErrorAnalytics>({
    error_details: [],
    error_trends: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;

    const fetchAnalytics = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Fetch metrics
        const { data: metricsData, error: metricsError } = await supabase.rpc(
          "get_submission_metrics",
          { user_id: user.id, days }
        );

        if (metricsError) throw metricsError;
        setMetrics(metricsData);

        // Fetch timeline
        const { data: timelineData, error: timelineError } = await supabase.rpc(
          "get_submission_timeline",
          { user_id: user.id, days }
        );

        if (timelineError) throw timelineError;
        setTimeline(timelineData);

        // Fetch error analytics
        const { data: errorData, error: errorError } = await supabase.rpc(
          "get_error_analytics",
          { user_id: user.id, days }
        );

        if (errorError) throw errorError;
        setErrorAnalytics(errorData);
      } catch (err) {
        console.error("Error fetching analytics:", err);
        setError(
          err instanceof Error ? err.message : "Failed to fetch analytics"
        );
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalytics();
  }, [user, days]);

  return {
    metrics,
    timeline,
    errorAnalytics,
    isLoading,
    error,
  };
}
