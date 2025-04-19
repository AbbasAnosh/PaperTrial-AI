import React, { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { FormField } from "@/types/form";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from "lucide-react";
import { cn } from "@/lib/utils";

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface FormPreviewProps {
  pdfUrl: string;
  fields: FormField[];
  activeField?: string;
  onFieldClick?: (field: FormField) => void;
}

export function FormPreview({
  pdfUrl,
  fields,
  activeField,
  onFieldClick,
}: FormPreviewProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [rotation, setRotation] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const [dimensions, setDimensions] = useState({
    width: 0,
    height: 0,
  });

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };

    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, []);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  };

  const zoomIn = () => setScale((prev) => Math.min(prev + 0.1, 2.0));
  const zoomOut = () => setScale((prev) => Math.max(prev - 0.1, 0.5));
  const nextPage = () => setCurrentPage((prev) => Math.min(prev + 1, numPages));
  const prevPage = () => setCurrentPage((prev) => Math.max(prev - 1, 1));

  const renderFieldHighlights = (pageFields: FormField[]) => {
    return pageFields.map((field, index) => {
      const { x, y } = field.coordinates;
      const isActive = field.name === activeField;

      return (
        <div
          key={`${field.name}-${index}`}
          className={cn(
            "absolute border-2 rounded transition-all cursor-pointer",
            isActive
              ? "border-primary bg-primary/20"
              : "border-muted-foreground/20 hover:border-primary/50 hover:bg-primary/10"
          )}
          style={{
            left: `${x * scale}px`,
            top: `${y * scale}px`,
            width: "100px", // You might want to get actual dimensions from the field
            height: "30px",
            transform: `rotate(${rotation}deg)`,
          }}
          onClick={() => onFieldClick?.(field)}
        >
          <div className="absolute -top-6 left-0 text-xs bg-background px-2 py-1 rounded border">
            {field.name}
            {field.confidence && (
              <span className="ml-2 text-muted-foreground">
                {Math.round(field.confidence * 100)}%
              </span>
            )}
          </div>
        </div>
      );
    });
  };

  return (
    <Card className="p-4 h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="icon"
            onClick={prevPage}
            disabled={currentPage <= 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm">
            Page {currentPage} of {numPages}
          </span>
          <Button
            variant="outline"
            size="icon"
            onClick={nextPage}
            disabled={currentPage >= numPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="icon" onClick={zoomOut}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="text-sm w-16 text-center">
            {Math.round(scale * 100)}%
          </span>
          <Button variant="outline" size="icon" onClick={zoomIn}>
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto relative" ref={containerRef}>
        <Document
          file={pdfUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          className="flex justify-center"
        >
          <div className="relative">
            <Page
              pageNumber={currentPage}
              scale={scale}
              rotate={rotation}
              width={dimensions.width * 0.9}
            />
            {renderFieldHighlights(
              fields.filter((f) => f.page === currentPage)
            )}
          </div>
        </Document>
      </div>
    </Card>
  );
}
