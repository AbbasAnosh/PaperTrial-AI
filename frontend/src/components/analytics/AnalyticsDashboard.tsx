import React, { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LineChart, BarChart } from "@/components/ui/charts";
import { format } from "date-fns";
import { useAnalytics } from "@/hooks/useAnalytics";

export function AnalyticsDashboard() {
  const { metrics, timeline, errorAnalytics, isLoading } = useAnalytics();
  const [timeRange, setTimeRange] = useState<"7d" | "30d" | "90d">("30d");

  const getTimeRangeDays = (range: string) => {
    switch (range) {
      case "7d":
        return 7;
      case "30d":
        return 30;
      case "90d":
        return 90;
      default:
        return 30;
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ${seconds % 60}s`;
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Analytics Dashboard</h2>
        <Tabs
          value={timeRange}
          onValueChange={(value) => setTimeRange(value as any)}
        >
          <TabsList>
            <TabsTrigger value="7d">7 Days</TabsTrigger>
            <TabsTrigger value="30d">30 Days</TabsTrigger>
            <TabsTrigger value="90d">90 Days</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {isLoading ? (
        <div>Loading analytics...</div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="p-4">
              <h3 className="text-sm font-medium text-gray-500">
                Total Submissions
              </h3>
              <p className="text-2xl font-bold">{metrics.total_submissions}</p>
            </Card>
            <Card className="p-4">
              <h3 className="text-sm font-medium text-gray-500">
                Success Rate
              </h3>
              <p className="text-2xl font-bold">
                {Math.round(
                  ((metrics.status_counts?.completed || 0) /
                    metrics.total_submissions) *
                    100
                )}
                %
              </p>
            </Card>
            <Card className="p-4">
              <h3 className="text-sm font-medium text-gray-500">
                Avg Processing Time
              </h3>
              <p className="text-2xl font-bold">
                {formatDuration(metrics.avg_processing_time_ms || 0)}
              </p>
            </Card>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="p-4">
              <h3 className="text-lg font-medium mb-4">Submission Timeline</h3>
              <LineChart
                data={timeline.map((event) => ({
                  date: format(new Date(event.timestamp), "MMM d"),
                  value: 1,
                }))}
                xField="date"
                yField="value"
              />
            </Card>
            <Card className="p-4">
              <h3 className="text-lg font-medium mb-4">Error Distribution</h3>
              <BarChart
                data={Object.entries(metrics.error_counts || {}).map(
                  ([category, count]) => ({
                    category,
                    count,
                  })
                )}
                xField="category"
                yField="count"
              />
            </Card>
          </div>

          {/* Error Details */}
          <Card className="p-4">
            <h3 className="text-lg font-medium mb-4">Recent Errors</h3>
            <div className="space-y-4">
              {errorAnalytics.error_details.slice(0, 5).map((error, index) => (
                <div key={index} className="border-b pb-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">{error.category}</p>
                      <p className="text-sm text-gray-500">{error.message}</p>
                    </div>
                    <span className="text-sm text-gray-500">
                      {format(new Date(error.timestamp), "MMM d, yyyy")}
                    </span>
                  </div>
                  {error.details && (
                    <pre className="mt-2 text-sm bg-gray-50 p-2 rounded">
                      {JSON.stringify(error.details, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
