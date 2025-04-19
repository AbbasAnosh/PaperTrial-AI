import { useEffect, useState } from "react";
import {
  FormGuidance as FormGuidanceType,
  FormTemplateService,
} from "@/services/formTemplateService";
import { AIService } from "@/services/aiService";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Info, AlertCircle, CheckCircle2 } from "lucide-react";
import { FormTemplate } from "@/types/form";

interface FormGuidanceProps {
  formId: string;
  currentStep: number;
  template: FormTemplate;
  formData: Record<string, any>;
}

export const FormGuidance = ({
  formId,
  currentStep,
  template,
  formData,
}: FormGuidanceProps) => {
  const [guidance, setGuidance] = useState<FormGuidanceType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadGuidance = async () => {
      try {
        // First try to get pre-generated guidance
        const guidanceList = await FormTemplateService.getFormGuidance(formId);
        let currentGuidance = guidanceList.find((g) => g.step === currentStep);

        // If no pre-generated guidance exists, generate it using AI
        if (!currentGuidance) {
          const aiGuidance = await AIService.generateFormGuidance(
            formId,
            currentStep,
            {
              previousAnswers: formData,
              currentFields: template.steps[currentStep].fields,
            }
          );

          currentGuidance = {
            id: `${formId}-${currentStep}`,
            formId,
            step: currentStep,
            ...aiGuidance,
          };

          // Save the generated guidance for future use
          await FormTemplateService.createFormGuidance(currentGuidance);
        }

        setGuidance(currentGuidance);
      } catch (error) {
        console.error("Error loading form guidance:", error);
      } finally {
        setLoading(false);
      }
    };

    loadGuidance();
  }, [formId, currentStep, template, formData]);

  if (loading) {
    return <div>Loading guidance...</div>;
  }

  if (!guidance) {
    return null;
  }

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>Step {currentStep + 1} Guidance</CardTitle>
        <CardDescription>AI-powered assistance for this step</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="prose max-w-none">
          <p>{guidance.content}</p>
        </div>

        {guidance.tips && guidance.tips.length > 0 && (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>Tips</AlertTitle>
            <AlertDescription>
              <ul className="list-disc pl-4">
                {guidance.tips.map((tip, index) => (
                  <li key={index}>{tip}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {guidance.commonMistakes && guidance.commonMistakes.length > 0 && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Common Mistakes</AlertTitle>
            <AlertDescription>
              <ul className="list-disc pl-4">
                {guidance.commonMistakes.map((mistake, index) => (
                  <li key={index}>{mistake}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {guidance.requiredDocuments &&
          guidance.requiredDocuments.length > 0 && (
            <Alert variant="default">
              <CheckCircle2 className="h-4 w-4" />
              <AlertTitle>Required Documents</AlertTitle>
              <AlertDescription>
                <ul className="list-disc pl-4">
                  {guidance.requiredDocuments.map((doc, index) => (
                    <li key={index}>{doc}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}

        <div className="text-sm text-muted-foreground">
          Estimated time: {guidance.estimatedTime}
        </div>
      </CardContent>
    </Card>
  );
};
