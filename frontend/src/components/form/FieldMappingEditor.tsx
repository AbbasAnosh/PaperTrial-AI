import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle, Save, RefreshCw } from "lucide-react";
import { FormField } from "@/types/form";

interface FieldMappingEditorProps {
  formFields: FormField[];
  detectedFields: FormField[];
  onSave: (mappings: Record<string, string>) => void;
  onRetry: () => void;
  isLoading?: boolean;
}

export function FieldMappingEditor({
  formFields,
  detectedFields,
  onSave,
  onRetry,
  isLoading = false,
}: FieldMappingEditorProps) {
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<string[]>([]);

  // Initialize mappings when props change
  useEffect(() => {
    const initialMappings: Record<string, string> = {};
    detectedFields.forEach((field) => {
      initialMappings[field.name] = field.name;
    });
    setMappings(initialMappings);
  }, [detectedFields]);

  const handleMappingChange = (fieldName: string, targetField: string) => {
    setMappings((prev) => ({
      ...prev,
      [fieldName]: targetField,
    }));
  };

  const validateMappings = () => {
    const newErrors: string[] = [];

    // Check for duplicate mappings
    const usedTargets = new Set<string>();
    Object.entries(mappings).forEach(([source, target]) => {
      if (usedTargets.has(target)) {
        newErrors.push(`Multiple fields are mapped to "${target}"`);
      }
      usedTargets.add(target);
    });

    // Check for required fields
    formFields.forEach((field) => {
      if (field.required && !Object.values(mappings).includes(field.name)) {
        newErrors.push(`Required field "${field.name}" is not mapped`);
      }
    });

    setErrors(newErrors);
    return newErrors.length === 0;
  };

  const handleSave = () => {
    if (validateMappings()) {
      onSave(mappings);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">Field Mappings</h3>
        <div className="space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            disabled={isLoading}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry Detection
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={isLoading || errors.length > 0}
          >
            <Save className="h-4 w-4 mr-2" />
            Save Mappings
          </Button>
        </div>
      </div>

      {errors.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Validation Errors</AlertTitle>
          <AlertDescription>
            <ul className="list-disc list-inside">
              {errors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4">
        {detectedFields.map((field) => (
          <Card key={field.name} className="p-4">
            <div className="grid gap-2">
              <Label>Detected Field: {field.name}</Label>
              <Select
                value={mappings[field.name]}
                onValueChange={(value) =>
                  handleMappingChange(field.name, value)
                }
                disabled={isLoading}
              >
                <option value="">Select target field</option>
                {formFields.map((targetField) => (
                  <option
                    key={targetField.name}
                    value={targetField.name}
                    disabled={
                      Object.values(mappings).includes(targetField.name) &&
                      mappings[field.name] !== targetField.name
                    }
                  >
                    {targetField.name}{" "}
                    {targetField.required ? "(Required)" : ""}
                  </option>
                ))}
              </Select>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
