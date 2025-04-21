import React, { useState, useEffect } from "react";
import { Upload, Table, Button, Card, message, Popconfirm, Space } from "antd";
import {
  UploadOutlined,
  DeleteOutlined,
  DownloadOutlined,
} from "@ant-design/icons";
import ProcessTracker from "./ProcessTracker";

const DocumentManager = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(-1);
  const [processingStatus, setProcessingStatus] = useState("wait");

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await fetch("/api/user/documents");
      const data = await response.json();
      setDocuments(data);
    } catch (error) {
      message.error("Failed to load documents");
    }
  };

  const handleUpload = async (file) => {
    console.log("Starting upload process...");
    setCurrentStep(0);
    setProcessingStatus("process");
    console.log("Step 0: Upload started");
    const formData = new FormData();
    formData.append("file", file);

    try {
      console.log("Sending file to server...");
      const response = await fetch("/api/documents/upload", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        console.log("Upload successful, moving to processing...");
        setCurrentStep(1);
        message.success("Document uploaded successfully");

        // Simulate processing
        setTimeout(() => {
          console.log("Step 2: Processing started");
          setCurrentStep(2);
          // Simulate form generation
          setTimeout(() => {
            console.log("Step 3: Form generation started");
            setCurrentStep(3);
            // Simulate review ready
            setTimeout(() => {
              console.log("Step 4: Process completed");
              setCurrentStep(4);
              setProcessingStatus("finish");
              message.success("Document processing completed");
              fetchDocuments();
            }, 1000);
          }, 1000);
        }, 1000);
      } else {
        throw new Error("Upload failed");
      }
    } catch (error) {
      console.error("Error during upload:", error);
      setProcessingStatus("error");
      message.error("Failed to upload document");
    }
    return false;
  };

  const handleDelete = async (documentId) => {
    try {
      const response = await fetch(`/api/user/documents/${documentId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        message.success("Document deleted successfully");
        fetchDocuments();
      } else {
        throw new Error("Delete failed");
      }
    } catch (error) {
      message.error("Failed to delete document");
    }
  };

  const handleDownload = async (documentId) => {
    try {
      const response = await fetch(`/api/documents/${documentId}/download`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `document-${documentId}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
      } else {
        throw new Error("Download failed");
      }
    } catch (error) {
      message.error("Failed to download document");
    }
  };

  const columns = [
    {
      title: "File Name",
      dataIndex: "file_name",
      key: "file_name",
    },
    {
      title: "Type",
      dataIndex: "file_type",
      key: "file_type",
    },
    {
      title: "Upload Date",
      dataIndex: "created_at",
      key: "created_at",
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, record) => (
        <Space>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record.id)}
          >
            Download
          </Button>
          <Popconfirm
            title="Are you sure you want to delete this document?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card title="Document Manager">
      <ProcessTracker currentStep={currentStep} status={processingStatus} />

      <Upload
        beforeUpload={handleUpload}
        showUploadList={false}
        accept=".pdf,.doc,.docx"
      >
        <Button icon={<UploadOutlined />}>Upload Document</Button>
      </Upload>

      <Table
        dataSource={documents}
        columns={columns}
        rowKey="id"
        loading={loading}
        style={{ marginTop: 16 }}
      />
    </Card>
  );
};

export default DocumentManager;
