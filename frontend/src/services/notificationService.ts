import { supabase } from "@/integrations/supabase/client";
import { FormSubmission } from "@/types/form";

export class NotificationService {
  static async sendSubmissionConfirmation(submission: FormSubmission) {
    try {
      // Get user preferences
      const { data: userPreferences } = await supabase
        .from("user_preferences")
        .select("email_notifications, sms_notifications, phone_number")
        .eq("user_id", submission.userId)
        .single();

      if (!userPreferences) return;

      // Send email notification if enabled
      if (userPreferences.email_notifications) {
        await this.sendEmailNotification(submission);
      }

      // Send SMS notification if enabled and phone number exists
      if (userPreferences.sms_notifications && userPreferences.phone_number) {
        await this.sendSMSNotification(
          submission,
          userPreferences.phone_number
        );
      }
    } catch (error) {
      console.error("Error sending notifications:", error);
    }
  }

  private static async sendEmailNotification(submission: FormSubmission) {
    const { data, error } = await supabase.functions.invoke("send-email", {
      body: {
        to: submission.userId, // This should be the user's email
        subject: "Form Submission Confirmation",
        text: `Your form submission (${submission.formId}) has been received and is being processed.`,
        html: `
          <h1>Form Submission Confirmation</h1>
          <p>Your form submission (${submission.formId}) has been received and is being processed.</p>
          <p>Status: ${submission.status}</p>
          <p>Submission ID: ${submission.id}</p>
        `,
      },
    });

    if (error) throw error;
    return data;
  }

  private static async sendSMSNotification(
    submission: FormSubmission,
    phoneNumber: string
  ) {
    const { data, error } = await supabase.functions.invoke("send-sms", {
      body: {
        to: phoneNumber,
        message: `Your form submission (${submission.formId}) has been received. Status: ${submission.status}`,
      },
    });

    if (error) throw error;
    return data;
  }

  static async sendStatusUpdate(submission: FormSubmission, newStatus: string) {
    try {
      // Get user preferences
      const { data: userPreferences } = await supabase
        .from("user_preferences")
        .select("email_notifications, sms_notifications, phone_number")
        .eq("user_id", submission.userId)
        .single();

      if (!userPreferences) return;

      // Send email notification if enabled
      if (userPreferences.email_notifications) {
        await this.sendEmailStatusUpdate(submission, newStatus);
      }

      // Send SMS notification if enabled and phone number exists
      if (userPreferences.sms_notifications && userPreferences.phone_number) {
        await this.sendSMSStatusUpdate(
          submission,
          newStatus,
          userPreferences.phone_number
        );
      }
    } catch (error) {
      console.error("Error sending status update notifications:", error);
    }
  }

  private static async sendEmailStatusUpdate(
    submission: FormSubmission,
    newStatus: string
  ) {
    const { data, error } = await supabase.functions.invoke("send-email", {
      body: {
        to: submission.userId,
        subject: "Form Submission Status Update",
        text: `Your form submission (${submission.formId}) status has been updated to: ${newStatus}`,
        html: `
          <h1>Form Submission Status Update</h1>
          <p>Your form submission (${submission.formId}) status has been updated to: ${newStatus}</p>
          <p>Submission ID: ${submission.id}</p>
        `,
      },
    });

    if (error) throw error;
    return data;
  }

  private static async sendSMSStatusUpdate(
    submission: FormSubmission,
    newStatus: string,
    phoneNumber: string
  ) {
    const { data, error } = await supabase.functions.invoke("send-sms", {
      body: {
        to: phoneNumber,
        message: `Form submission (${submission.formId}) status updated to: ${newStatus}`,
      },
    });

    if (error) throw error;
    return data;
  }
}
