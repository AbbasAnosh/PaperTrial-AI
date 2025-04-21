import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Alert, AlertDescription } from "./ui/alert";
import { AlertCircle, Upload, FileText, Globe } from "lucide-react";
import { apiService } from "../services/api";
import { toast } from "react-hot-toast";

interface FormUploadProps {
  onUploadComplete: (formData: any) => void;
  onError: (error: string) => void;
}

export const FormUpload: React.FC<FormUploadProps> = ({
  onUploadComplete,
  onError,
}) => {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [webFormUrl, setWebFormUrl] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      if (file.type !== "application/pdf") {
        toast.error("Please upload a PDF file");
        return;
      }

      setIsProcessing(true);
      try {
        const response = await apiService.uploadPDF(file, (progress) => {
          setUploadProgress(progress);
        });
        toast.success("File uploaded successfully");
        onUploadComplete(response);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Upload failed");
        onError(error instanceof Error ? error.message : "Upload failed");
      } finally {
        setIsProcessing(false);
        setUploadProgress(0);
      }
    },
    [onUploadComplete, onError]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
    },
    maxFiles: 1,
  });

  const handleWebFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!webFormUrl) {
      toast.error("Please enter a web form URL");
      return;
    }

    setIsProcessing(true);
    try {
      const response = await apiService.processWebForm(webFormUrl);
      toast.success("Web form processed successfully");
      onUploadComplete(response);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Web form processing failed"
      );
      onError(
        error instanceof Error ? error.message : "Web form processing failed"
      );
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="space-y-4">
          <h2 className="text-2xl font-bold">Upload Form</h2>
          <p className="text-muted-foreground">
            Upload a PDF form or enter a web form URL to begin processing
          </p>

          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
              ${
                isDragActive
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25"
              }`}
          >
            <input {...getInputProps()} />
            <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">
              {isDragActive
                ? "Drop the PDF here"
                : "Drag and drop a PDF form here, or click to select"}
            </p>
          </div>

          {isProcessing && (
            <div className="space-y-2">
              <Progress value={uploadProgress} className="w-full" />
              <p className="text-sm text-muted-foreground text-center">
                {uploadProgress > 0
                  ? `Uploading... ${uploadProgress}%`
                  : "Processing your form..."}
              </p>
            </div>
          )}
        </div>
      </Card>

      <Card className="p-6">
        <form onSubmit={handleWebFormSubmit} className="space-y-4">
          <h2 className="text-2xl font-bold">Web Form</h2>
          <p className="text-muted-foreground">
            Enter the URL of a web form to process
          </p>

          <div className="space-y-2">
            <Label htmlFor="webFormUrl">Form URL</Label>
            <div className="flex gap-2">
              <Input
                id="webFormUrl"
                type="url"
                placeholder="https://example.com/form"
                value={webFormUrl}
                onChange={(e) => setWebFormUrl(e.target.value)}
                className="flex-1"
                disabled={isProcessing}
              />
              <Button type="submit" disabled={isProcessing}>
                {isProcessing ? "Processing..." : "Process"}
              </Button>
            </div>
          </div>
        </form>
      </Card>

      {isProcessing && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Processing your form... This may take a few moments.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};
