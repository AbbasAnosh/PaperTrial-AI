import React from "react";
import { Steps, Card } from "antd";
import {
  UploadOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
  CheckOutlined,
} from "@ant-design/icons";

const { Step } = Steps;

const ProcessTracker = ({ currentStep, status }) => {
  const steps = [
    {
      title: "Upload",
      icon: currentStep === 0 ? <LoadingOutlined /> : <UploadOutlined />,
      status:
        currentStep > 0 ? "finish" : currentStep === 0 ? "process" : "wait",
    },
    {
      title: "Processing",
      icon: currentStep === 1 ? <LoadingOutlined /> : <CheckCircleOutlined />,
      status:
        currentStep > 1 ? "finish" : currentStep === 1 ? "process" : "wait",
    },
    {
      title: "Form Generation",
      icon: currentStep === 2 ? <LoadingOutlined /> : <FileTextOutlined />,
      status:
        currentStep > 2 ? "finish" : currentStep === 2 ? "process" : "wait",
    },
    {
      title: "Review & Submit",
      icon: currentStep === 3 ? <LoadingOutlined /> : <CheckOutlined />,
      status:
        currentStep > 3 ? "finish" : currentStep === 3 ? "process" : "wait",
    },
  ];

  return (
    <Card style={{ marginBottom: 24 }}>
      <Steps current={currentStep} status={status}>
        {steps.map((step, index) => (
          <Step
            key={index}
            title={step.title}
            icon={step.icon}
            status={step.status}
          />
        ))}
      </Steps>
    </Card>
  );
};

export default ProcessTracker;
