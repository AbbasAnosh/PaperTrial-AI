import { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Upload, FileText, X } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/lib/supabase";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface FileUploadProps {
  onFileProcessed: (data: any) => void;
  onError: (error: string) => void;
  formType?: string;
}

export const FileUpload = ({
  onFileProcessed,
  onError,
  formType,
}: FileUploadProps) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const { toast } = useToast();
  const { user } = useAuth();

  // Subscribe to document status changes
  useEffect(() => {
    if (!documentId) return;

    const subscription = supabase
      .channel("document-status")
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "documents",
          filter: `id=eq.${documentId}`,
        },
        (payload) => {
          const newStatus = payload.new.status;
          if (newStatus === "processed") {
            setUploadProgress(100);
            onFileProcessed(payload.new);
            toast({
              title: "Success",
              description: "PDF processed successfully",
            });
          } else if (newStatus === "failed") {
            setUploadProgress(0);
            onError("Failed to process PDF");
            toast({
              title: "Error",
              description: "Failed to process PDF",
              variant: "destructive",
            });
          }
        }
      )
      .subscribe();

    return () => {
      subscription.unsubscribe();
    };
  }, [documentId, onFileProcessed, onError, toast]);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        const file = acceptedFiles[0];
        if (file.type === "application/pdf") {
          setFile(file);
          processFile(file);
        } else {
          toast({
            title: "Invalid File Type",
            description: "Please upload a PDF file.",
            variant: "destructive",
          });
        }
      }
    },
    [toast]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
    },
    maxFiles: 1,
  });

  const processFile = async (file: File) => {
    try {
      setUploadProgress(0);

      // Create FormData for file upload
      const formData = new FormData();
      formData.append("file", file);
      if (formType) {
        formData.append("form_type", formType);
      }

      // Upload file to FastAPI backend
      const response = await fetch(`${API_URL}/api/pdf/process`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to process PDF");
      }

      const data = await response.json();
      setDocumentId(data.document.id);
      setUploadProgress(50); // Initial processing started

      // Start polling for status updates
      const pollStatus = async () => {
        try {
          const statusResponse = await fetch(
            `${API_URL}/api/pdf/${data.document.id}`,
            {
              credentials: "include",
            }
          );

          if (!statusResponse.ok) {
            throw new Error("Failed to get document status");
          }

          const statusData = await statusResponse.json();
          if (statusData.document.status === "processed") {
            setUploadProgress(100);
            onFileProcessed(statusData.document);
          } else if (statusData.document.status === "failed") {
            throw new Error("PDF processing failed");
          } else {
            // Continue polling if still processing
            setTimeout(pollStatus, 2000);
          }
        } catch (error) {
          setUploadProgress(0);
          onError(
            error instanceof Error ? error.message : "Failed to process PDF"
          );
          toast({
            title: "Error",
            description: "Failed to process PDF",
            variant: "destructive",
          });
        }
      };

      pollStatus();
    } catch (error) {
      console.error("Error processing PDF:", error);
      onError(error instanceof Error ? error.message : "Failed to process PDF");
      toast({
        title: "Error",
        description: "Failed to process PDF",
        variant: "destructive",
      });
    }
  };

  const removeFile = () => {
    setFile(null);
    setUploadProgress(0);
    setDocumentId(null);
  };

  return (
    <Card className="p-6">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${
            isDragActive
              ? "border-primary bg-primary/5"
              : "border-gray-300 hover:border-primary"
          }`}
      >
        <input {...getInputProps()} />
        {!file ? (
          <div className="space-y-4">
            <Upload className="mx-auto h-12 w-12 text-gray-400" />
            <div>
              <p className="text-lg font-medium">
                {isDragActive
                  ? "Drop the PDF here"
                  : "Drag & drop a PDF file here"}
              </p>
              <p className="text-sm text-gray-500">or click to select a file</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-center space-x-2">
              <FileText className="h-8 w-8 text-primary" />
              <span className="font-medium">{file.name}</span>
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile();
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            {uploadProgress > 0 && uploadProgress < 100 && (
              <div className="space-y-2">
                <Progress value={uploadProgress} className="w-full" />
                <p className="text-sm text-gray-500">
                  {uploadProgress < 50
                    ? "Uploading PDF..."
                    : "Processing PDF..."}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
};
