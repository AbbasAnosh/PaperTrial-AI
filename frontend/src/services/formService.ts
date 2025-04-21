import { supabase } from "@/integrations/supabase/client";
import {
  FormProgress,
  FormSubmission,
  FormTemplate,
  FormField,
} from "@/types/form";
import { NotificationService } from "./notificationService";
import { SubmissionTimelineService } from "./submissionTimelineService";

export class FormService {
  static async saveProgress(
    userId: string,
    formId: string,
    currentStep: number,
    formData: Record<string, any>,
    screenshots: Record<number, string>
  ): Promise<FormProgress> {
    const { data, error } = await supabase
      .from("form_progress")
      .upsert({
        user_id: userId,
        form_id: formId,
        current_step: currentStep,
        form_data: formData,
        screenshots,
        status: "in_progress",
        updated_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  static async getProgress(
    userId: string,
    formId: string
  ): Promise<FormProgress | null> {
    const { data, error } = await supabase
      .from("form_progress")
      .select("*")
      .eq("user_id", userId)
      .eq("form_id", formId)
      .single();

    if (error) throw error;
    return data;
  }

  static async submitForm(
    userId: string,
    formId: string,
    formData: Record<string, any>,
    screenshots: Record<number, string>
  ): Promise<FormSubmission> {
    const { data, error } = await supabase
      .from("form_submissions")
      .insert({
        user_id: userId,
        form_id: formId,
        form_data: formData,
        screenshots,
        status: "submitted",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) throw error;

    // Create initial timeline event
    await SubmissionTimelineService.createTimelineEvent(
      data,
      "submission",
      "submitted",
      "Form submitted successfully"
    );

    // Send notification
    await NotificationService.sendSubmissionConfirmation(data);

    return data;
  }

  static async updateSubmissionStatus(
    submissionId: string,
    newStatus: string,
    message: string
  ): Promise<FormSubmission> {
    const { data: submission, error } = await supabase
      .from("form_submissions")
      .update({
        status: newStatus,
        updated_at: new Date().toISOString(),
      })
      .eq("id", submissionId)
      .select()
      .single();

    if (error) throw error;

    // Create timeline event
    await SubmissionTimelineService.createTimelineEvent(
      submission,
      "status_update",
      newStatus,
      message
    );

    // Send notification
    await NotificationService.sendStatusUpdate(submission, newStatus);

    return submission;
  }

  static async retrySubmission(
    submissionId: string,
    retryCount: number
  ): Promise<FormSubmission> {
    const { data, error } = await supabase
      .from("form_submissions")
      .update({
        retry_count: retryCount + 1,
        status: "pending",
        updated_at: new Date().toISOString(),
      })
      .eq("id", submissionId)
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  static async captureScreenshot(
    stepNumber: number,
    formId: string
  ): Promise<string> {
    // This is a placeholder for actual screenshot capture logic
    // You would typically use a library like html2canvas
    return `screenshot_${formId}_${stepNumber}_${Date.now()}.png`;
  }

  static async handleConditionalFields(
    template: FormTemplate,
    formData: Record<string, any>
  ): Promise<FormField[]> {
    const visibleFields: FormField[] = [];

    for (const step of template.steps) {
      for (const field of step.fields) {
        if (!field.conditional) {
          visibleFields.push(field);
          continue;
        }

        const { field: conditionalField, value, show } = field.conditional;
        const fieldValue = formData[conditionalField];

        if (show === (fieldValue === value)) {
          visibleFields.push(field);
        }
      }
    }

    return visibleFields;
  }
}
