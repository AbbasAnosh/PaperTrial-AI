import React, { useState, useEffect } from "react";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { RadioGroup, RadioGroupItem } from "./ui/radio-group";
import { Label } from "./ui/label";
import { Checkbox } from "./ui/checkbox";
import { Progress } from "./ui/progress";
import { ChevronLeft, ChevronRight, Send } from "lucide-react";
import { apiService } from "../services/api";
import { toast } from "react-hot-toast";

interface FormField {
  id: string;
  name: string;
  type: string;
  required: boolean;
  options?: string[];
}

interface QuestionAnswerProps {
  formId: string;
  fields: FormField[];
  onComplete: (answers: Record<string, any>) => void;
  onCancel: () => void;
}

export const QuestionAnswer: React.FC<QuestionAnswerProps> = ({
  formId,
  fields,
  onComplete,
  onCancel,
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [currentAnswer, setCurrentAnswer] = useState<any>("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentField = fields[currentIndex];
  const progress = ((currentIndex + 1) / fields.length) * 100;

  const handleNext = async () => {
    if (currentField.required && !currentAnswer) {
      return; // Don't proceed if required field is empty
    }

    const newAnswers = { ...answers, [currentField.id]: currentAnswer };
    setAnswers(newAnswers);

    if (currentIndex === fields.length - 1) {
      setIsSubmitting(true);
      try {
        const response = await apiService.submitForm(formId, newAnswers);
        toast.success("Form submitted successfully");
        onComplete(response);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to submit form");
        setIsSubmitting(false);
      }
    } else {
      setCurrentIndex(currentIndex + 1);
      setCurrentAnswer(answers[fields[currentIndex + 1].id] || "");
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setCurrentAnswer(answers[fields[currentIndex - 1].id] || "");
    }
  };

  const renderInput = () => {
    switch (currentField.type.toLowerCase()) {
      case "text":
        return (
          <Input
            value={currentAnswer}
            onChange={(e) => setCurrentAnswer(e.target.value)}
            placeholder={`Enter ${currentField.name.toLowerCase()}`}
          />
        );
      case "textarea":
        return (
          <Textarea
            value={currentAnswer}
            onChange={(e) => setCurrentAnswer(e.target.value)}
            placeholder={`Enter ${currentField.name.toLowerCase()}`}
          />
        );
      case "radio":
        return (
          <RadioGroup value={currentAnswer} onValueChange={setCurrentAnswer}>
            {currentField.options?.map((option) => (
              <div key={option} className="flex items-center space-x-2">
                <RadioGroupItem value={option} id={option} />
                <Label htmlFor={option}>{option}</Label>
              </div>
            ))}
          </RadioGroup>
        );
      case "checkbox":
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              id={currentField.id}
              checked={currentAnswer}
              onCheckedChange={setCurrentAnswer}
            />
            <Label htmlFor={currentField.id}>{currentField.name}</Label>
          </div>
        );
      default:
        return (
          <Input
            value={currentAnswer}
            onChange={(e) => setCurrentAnswer(e.target.value)}
            placeholder={`Enter ${currentField.name.toLowerCase()}`}
          />
        );
    }
  };

  return (
    <Card className="p-6">
      <div className="space-y-6">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">
              Question {currentIndex + 1} of {fields.length}
            </h2>
            <span className="text-sm text-muted-foreground">
              {Math.round(progress)}% Complete
            </span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-medium">
            {currentField.name}
            {currentField.required && (
              <span className="text-red-500 ml-1">*</span>
            )}
          </h3>
          {renderInput()}
        </div>

        {error && <div className="text-red-500 text-sm">{error}</div>}

        <div className="flex items-center justify-between pt-4">
          <Button
            variant="outline"
            onClick={handlePrevious}
            disabled={currentIndex === 0 || isSubmitting}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            Previous
          </Button>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleNext}
              disabled={
                (currentField.required && !currentAnswer) || isSubmitting
              }
            >
              {currentIndex === fields.length - 1 ? (
                <>
                  {isSubmitting ? "Submitting..." : "Complete"}
                  <Send className="ml-2 h-4 w-4" />
                </>
              ) : (
                <>
                  Next
                  <ChevronRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
};
