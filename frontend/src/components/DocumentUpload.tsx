
import React, { useCallback } from 'react';
import { Upload } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';

interface DocumentUploadProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

export function DocumentUpload({ onFileSelect, disabled }: DocumentUploadProps) {
  const [dragActive, setDragActive] = React.useState(false);
  const [file, setFile] = React.useState<File | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setFile(file);
      onFileSelect(file);
    }
  }, [onFileSelect]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setFile(file);
      onFileSelect(file);
    }
  }, [onFileSelect]);

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <div
        className={cn(
          "flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-lg transition-colors",
          dragActive ? "border-blue-500 bg-blue-50" : "border-gray-300",
          "hover:border-blue-500 hover:bg-blue-50",
          disabled && "opacity-50 cursor-not-allowed"
        )}
        onDragEnter={!disabled ? handleDrag : undefined}
        onDragLeave={!disabled ? handleDrag : undefined}
        onDragOver={!disabled ? handleDrag : undefined}
        onDrop={!disabled ? handleDrop : undefined}
      >
        <Upload className="w-12 h-12 text-gray-400 mb-4" />
        <p className="text-lg font-medium text-gray-700 mb-2">
          {file ? file.name : "Drop your document here"}
        </p>
        <p className="text-sm text-gray-500 mb-4">
          or click to select files
        </p>
        <input
          type="file"
          className="hidden"
          onChange={handleChange}
          accept=".pdf,.doc,.docx"
          id="file-upload"
          disabled={disabled}
        />
        <label
          htmlFor="file-upload"
          className={cn(
            "cursor-pointer bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        >
          Select File
        </label>
      </div>
    </Card>
  );
}
