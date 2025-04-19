import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  FormField,
  FormTemplate,
  FormProgress as FormProgressType,
} from "@/types/form";
import { FormProgress } from "./FormProgress";
import { FormNavigation } from "./FormNavigation";
import { FormErrorDisplay } from "./FormErrorDisplay";
import { FormGuidance } from "./FormGuidance";
import { FormService } from "@/services/formService";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/components/ui/use-toast";
import html2canvas from "html2canvas";

interface DynamicFormProps {
  template: FormTemplate & {
    maxRetries?: number;
    retryDelay?: number;
  };
  onFormSubmit: (data: Record<string, any>) => Promise<void>;
  onError?: (error: Error) => void;
}

// Add this before the DynamicForm component
const createFormSchema = (fields: FormField[]) => {
  const schema: Record<string, any> = {};
  fields.forEach((field) => {
    let fieldSchema: z.ZodType<any>;

    switch (field.type) {
      case "number":
        fieldSchema = z.number();
        break;
      case "email":
        fieldSchema = z.string().email();
        break;
      case "date":
        fieldSchema = z.string().datetime();
        break;
      default:
        fieldSchema = z.string();
    }

    schema[field.name] = field.required ? fieldSchema : fieldSchema.optional();
  });
  return z.object(schema);
};

export function DynamicForm({
  template,
  onFormSubmit: handleFormSubmit,
  onError,
}: DynamicFormProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [screenshots, setScreenshots] = useState<Record<number, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [savedProgress, setSavedProgress] = useState<FormProgressType | null>(
    null
  );
  const [retryCount, setRetryCount] = useState(0);
  const [visibleFields, setVisibleFields] = useState<FormField[]>([]);
  const maxRetries = template.maxRetries || 3;
  const retryDelay = template.retryDelay || 5000;

  const formSchema = createFormSchema(
    template.steps.flatMap((step) => step.fields)
  );
  type FormData = z.infer<typeof formSchema>;

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<FormData>({
    defaultValues: {},
    resolver: zodResolver(formSchema),
  });

  // Load saved progress
  useEffect(() => {
    const loadProgress = async () => {
      if (!user) return;
      try {
        const progress = await FormService.getProgress(user.id, template.id);
        if (progress) {
          setSavedProgress(progress);
          setCurrentStep(progress.currentStep);
          setFormData(progress.formData);
          setScreenshots(progress.screenshots);
        }
      } catch (error) {
        console.error("Error loading progress:", error);
      }
    };
    loadProgress();
  }, [user, template.id]);

  // Handle conditional fields
  useEffect(() => {
    const loadFields = async () => {
      const fields = await FormService.handleConditionalFields(
        template,
        formData
      );
      setVisibleFields(fields);
    };
    loadFields();
  }, [template, formData]);

  const currentFields = visibleFields.slice(
    currentStep * 5,
    (currentStep + 1) * 5
  );

  const captureScreenshot = async () => {
    const formElement = document.getElementById("form-content");
    if (!formElement) return;

    try {
      const canvas = await html2canvas(formElement);
      const screenshot = canvas.toDataURL("image/png");
      setScreenshots((prev) => ({ ...prev, [currentStep]: screenshot }));
      return screenshot;
    } catch (error) {
      console.error("Error capturing screenshot:", error);
    }
  };

  const saveProgress = async (data: Record<string, any>) => {
    if (!user) return;
    try {
      const screenshot = await captureScreenshot();
      await FormService.saveProgress(
        user.id,
        template.id,
        currentStep,
        { ...formData, ...data },
        { ...screenshots, [currentStep]: screenshot || "" }
      );
      toast({
        title: "Progress Saved",
        description: "Your form progress has been saved.",
      });
    } catch (error) {
      console.error("Error saving progress:", error);
      toast({
        title: "Error",
        description: "Failed to save progress. Please try again.",
        variant: "destructive",
      });
    }
  };

  const onSubmit = async (data: Record<string, any>) => {
    setIsSubmitting(true);
    try {
      const newData = { ...formData, ...data };
      setFormData(newData);

      if (currentStep < template.steps.length - 1) {
        await saveProgress(newData);
        setCurrentStep(currentStep + 1);
      } else {
        const screenshot = await captureScreenshot();
        const submission = await FormService.submitForm(
          user?.id || "",
          template.id,
          newData,
          { ...screenshots, [currentStep]: screenshot || "" }
        );
        handleFormSubmit(submission);
      }
    } catch (error) {
      if (retryCount < maxRetries) {
        setRetryCount(retryCount + 1);
        setTimeout(() => {
          onSubmit(data);
        }, retryDelay);
      } else {
        const err =
          error instanceof Error ? error : new Error("Failed to submit form");
        if (onError) {
          onError(err);
        }
        toast({
          title: "Error",
          description: "Failed to submit form. Please try again later.",
          variant: "destructive",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const onPrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  return (
    <div className="space-y-6">
      <FormProgress
        title={template?.name || "Form"}
        currentStep={currentStep}
        totalSteps={template.steps.length}
      />

      <form
        id="form-content"
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-6"
      >
        <Card>
          <CardHeader>
            <CardTitle>
              {template?.steps?.[currentStep]?.title || "Step"}
            </CardTitle>
            <CardDescription>
              {template?.steps?.[currentStep]?.description || ""}
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {template?.steps?.[currentStep]?.fields?.map((field) => (
              <div key={field.id} className="space-y-2">
                <label className="text-sm font-medium">
                  {field.label}
                  {field.required && <span className="text-red-500">*</span>}
                </label>

                <input
                  type={field.type}
                  {...register(field.name)}
                  className="w-full p-2 border rounded-md"
                  placeholder={field.placeholder}
                  required={field.required}
                />

                {errors[field.name] && (
                  <FormErrorDisplay
                    hasError={true}
                    retryCount={retryCount}
                    onRetry={() => handleSubmit(onSubmit)()}
                  />
                )}
              </div>
            ))}
          </CardContent>

          <CardFooter className="flex justify-between">
            <Button
              type="button"
              variant="outline"
              onClick={onPrevious}
              disabled={currentStep === 0}
            >
              Previous
            </Button>

            <Button type="submit" disabled={isSubmitting}>
              {currentStep === (template?.steps?.length || 0) - 1
                ? "Submit"
                : "Next"}
            </Button>
          </CardFooter>
        </Card>
      </form>

      <FormNavigation
        currentStep={currentStep}
        totalSteps={template?.steps?.length || 0}
        onPrevious={onPrevious}
        onNext={() => handleSubmit(onSubmit)()}
        isSubmitting={isSubmitting}
        savedProgress={!!savedProgress}
        onSave={() => saveProgress(watch() as Record<string, any>)}
        onScreenshot={captureScreenshot}
      />

      {currentStep < template.steps.length && (
        <FormGuidance
          formId={template.id}
          currentStep={currentStep}
          template={template}
          formData={formData}
        />
      )}
    </div>
  );
}
