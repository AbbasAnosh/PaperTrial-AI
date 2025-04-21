import React, { useEffect, useState } from "react";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
import { Button } from "./ui/button";
import { Check, AlertTriangle } from "lucide-react";
import { apiService } from "../services/api";

interface FormField {
  id: string;
  name: string;
  type: string;
  confidence: number;
  required: boolean;
  page: number;
  coordinates: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

interface FormPreviewProps {
  formId: string;
  fields: FormField[];
  onStartQA: () => void;
  onEditFields: () => void;
}

export const FormPreview: React.FC<FormPreviewProps> = ({
  formId,
  fields: initialFields,
  onStartQA,
  onEditFields,
}) => {
  const [fields, setFields] = useState<FormField[]>(initialFields);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFields = async () => {
      try {
        const response = await apiService.getFormFields(formId);
        setFields(response);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load form fields"
        );
      } finally {
        setIsLoading(false);
      }
    };

    // Only fetch if initialFields is empty
    if (initialFields.length === 0) {
      setIsLoading(true);
      fetchFields();
    }

    // Set up WebSocket connection for real-time updates
    const ws = new WebSocket(`${import.meta.env.VITE_WS_URL}/forms/${formId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "FIELD_UPDATE") {
        setFields((prevFields) =>
          prevFields.map((field) =>
            field.id === data.field.id ? data.field : field
          )
        );
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    return () => {
      ws.close();
    };
  }, [formId, initialFields]);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "bg-green-500";
    if (confidence >= 0.6) return "bg-yellow-500";
    return "bg-red-500";
  };

  const getFieldTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "text":
        return "📝";
      case "checkbox":
        return "☑️";
      case "radio":
        return "⭕";
      case "select":
        return "📋";
      case "date":
        return "📅";
      default:
        return "❓";
    }
  };

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading form fields...</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center h-64">
          <p className="text-red-500">{error}</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Form Preview</h2>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onEditFields}>
              Edit Fields
            </Button>
            <Button onClick={onStartQA}>Start Q&A Process</Button>
          </div>
        </div>

        <p className="text-muted-foreground">
          Review the detected form fields. Fields with low confidence scores may
          need manual verification.
        </p>

        <ScrollArea className="h-[500px] rounded-md border p-4">
          <div className="space-y-4">
            {fields.map((field) => (
              <Card key={field.id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">
                        {getFieldTypeIcon(field.type)}
                      </span>
                      <h3 className="font-medium">{field.name}</h3>
                      {field.required && (
                        <Badge variant="destructive">Required</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Type: {field.type} • Page: {field.page}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      className={getConfidenceColor(field.confidence)}
                      variant="secondary"
                    >
                      {Math.round(field.confidence * 100)}% confidence
                    </Badge>
                    {field.confidence < 0.6 && (
                      <AlertTriangle className="h-4 w-4 text-yellow-500" />
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </ScrollArea>

        <div className="flex items-center justify-between border-t pt-4">
          <div className="flex items-center gap-2">
            <Check className="h-4 w-4 text-green-500" />
            <span className="text-sm text-muted-foreground">
              {fields.filter((f) => f.confidence >= 0.8).length} fields with
              high confidence
            </span>
          </div>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
            <span className="text-sm text-muted-foreground">
              {fields.filter((f) => f.confidence < 0.6).length} fields need
              verification
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
};
