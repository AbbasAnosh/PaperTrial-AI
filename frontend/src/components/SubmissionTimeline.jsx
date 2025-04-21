import React, { useEffect, useState } from "react";
import { Timeline, TimelineItem } from "react-chrono";
import { Badge, Button, Card, Space, Typography } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import { useWebSocket } from "../hooks/useWebSocket";

const { Title, Text } = Typography;

const SubmissionTimeline = () => {
  const [submissions, setSubmissions] = useState([]);
  const { lastMessage } = useWebSocket();

  useEffect(() => {
    fetchSubmissions();
  }, []);

  useEffect(() => {
    if (lastMessage) {
      const updatedSubmission = JSON.parse(lastMessage.data);
      setSubmissions((prev) =>
        prev.map((sub) =>
          sub.id === updatedSubmission.id ? updatedSubmission : sub
        )
      );
    }
  }, [lastMessage]);

  const fetchSubmissions = async () => {
    try {
      const response = await fetch("/api/submissions");
      const data = await response.json();
      setSubmissions(data);
    } catch (error) {
      console.error("Error fetching submissions:", error);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircleOutlined style={{ color: "#52c41a" }} />;
      case "failed":
        return <CloseCircleOutlined style={{ color: "#f5222d" }} />;
      case "in_progress":
        return <SyncOutlined spin style={{ color: "#1890ff" }} />;
      default:
        return <ClockCircleOutlined style={{ color: "#faad14" }} />;
    }
  };

  const handleRetry = async (submissionId) => {
    try {
      const response = await fetch(`/api/submissions/${submissionId}/retry`, {
        method: "POST",
      });
      const data = await response.json();
      if (data.new_submission_id) {
        fetchSubmissions();
      }
    } catch (error) {
      console.error("Error retrying submission:", error);
    }
  };

  const items = submissions.map((submission) => ({
    title: new Date(submission.created_at).toLocaleString(),
    cardTitle: submission.form_id,
    cardSubtitle: (
      <Space>
        <Badge
          status={
            submission.status === "completed"
              ? "success"
              : submission.status === "failed"
              ? "error"
              : submission.status === "in_progress"
              ? "processing"
              : "default"
          }
          text={submission.status}
        />
        {submission.status === "failed" && (
          <Button type="link" onClick={() => handleRetry(submission.id)}>
            Retry
          </Button>
        )}
      </Space>
    ),
    cardDetailedText: submission.message || "No message available",
    icon: getStatusIcon(submission.status),
  }));

  return (
    <Card>
      <Title level={2}>Submission Timeline</Title>
      <Timeline
        items={items}
        mode="VERTICAL_ALTERNATING"
        theme={{
          primary: "#1890ff",
          secondary: "#f0f0f0",
          cardBgColor: "#fff",
          titleColor: "#000",
          titleColorActive: "#1890ff",
        }}
      />
    </Card>
  );
};

export default SubmissionTimeline;
