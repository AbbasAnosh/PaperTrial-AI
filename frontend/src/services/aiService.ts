import { FormTemplate, FormField } from "@/types/form";
import { supabase } from "@/lib/supabase";

export class AIService {
  static async analyzeFormData(
    formId: string,
    formData: Record<string, any>,
    fields: FormField[]
  ): Promise<{
    suggestions: Record<string, string>;
    confidence: number;
    validationErrors: string[];
  }> {
    const { data, error } = await supabase.functions.invoke("analyze-form", {
      body: {
        formId,
        formData,
        fields,
      },
    });

    if (error) throw error;
    return data;
  }

  static async generateFormGuidance(
    formId: string,
    step: number,
    context: {
      previousAnswers?: Record<string, any>;
      currentFields: FormField[];
    }
  ): Promise<{
    content: string;
    tips: string[];
    commonMistakes: string[];
    estimatedTime: string;
    requiredDocuments: string[];
  }> {
    const { data, error } = await supabase.functions.invoke(
      "generate-guidance",
      {
        body: {
          formId,
          step,
          context,
        },
      }
    );

    if (error) throw error;
    return data;
  }

  static async validateFormData(
    formId: string,
    formData: Record<string, any>,
    fields: FormField[]
  ): Promise<{
    isValid: boolean;
    errors: Record<string, string>;
    suggestions: Record<string, string>;
  }> {
    const { data, error } = await supabase.functions.invoke("validate-form", {
      body: {
        formId,
        formData,
        fields,
      },
    });

    if (error) throw error;
    return data;
  }

  static async extractFormData(
    documentUrl: string,
    formTemplate: FormTemplate
  ): Promise<Record<string, any>> {
    const { data, error } = await supabase.functions.invoke(
      "extract-form-data",
      {
        body: {
          documentUrl,
          formTemplate,
        },
      }
    );

    if (error) throw error;
    return data;
  }

  static async generateFormSummary(
    formId: string,
    formData: Record<string, any>
  ): Promise<{
    summary: string;
    nextSteps: string[];
    potentialIssues: string[];
  }> {
    const { data, error } = await supabase.functions.invoke(
      "generate-summary",
      {
        body: {
          formId,
          formData,
        },
      }
    );

    if (error) throw error;
    return data;
  }
}
