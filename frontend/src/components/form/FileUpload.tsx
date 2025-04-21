import { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Upload, FileText, X } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/integrations/supabase/client";
import { api } from "@/integrations/api/client";

interface Document {
  id: string;
  status: string;
  filename: string;
  extracted_fields?: Record<string, any>;
}

interface ProcessResponse {
  document: Document;
  message: string;
}

interface StatusResponse {
  document: Document;
}

interface FileUploadProps {
  onFileProcessed: (data: Document) => void;
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
            onFileProcessed(payload.new as Document);
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
      if (!user) {
        throw new Error("Please sign in to upload files");
      }

      setUploadProgress(0);

      // Create FormData for file upload
      const formData = new FormData();
      formData.append("file", file);
      if (formType) {
        formData.append("form_type", formType);
      }

      // Upload file using our API client
      const response = await api.post<ProcessResponse>(
        "/api/pdf/process",
        formData,
        {
          isFormData: true,
        }
      );

      setDocumentId(response.document.id);
      setUploadProgress(50); // Initial processing started

      // Start polling for status updates
      const pollStatus = async () => {
        try {
          const statusData = await api.get<StatusResponse>(
            `/api/pdf/${response.document.id}`
          );

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
            description:
              error instanceof Error ? error.message : "Failed to process PDF",
            variant: "destructive",
          });
        }
      };

      pollStatus();
    } catch (error) {
      setUploadProgress(0);
      onError(error instanceof Error ? error.message : "Failed to process PDF");
      toast({
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to process PDF",
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
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive ? "border-primary bg-primary/5" : "border-muted"
        }`}
      >
        <input {...getInputProps()} />
        {file ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>{file.name}</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                removeFile();
              }}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Drag and drop your PDF here, or click to select
            </p>
          </div>
        )}
      </div>
      {uploadProgress > 0 && (
        <div className="mt-4">
          <Progress value={uploadProgress} className="h-2" />
        </div>
      )}
    </Card>
  );
};
