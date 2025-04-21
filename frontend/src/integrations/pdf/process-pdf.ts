import { api } from "@/integrations/api/client";

interface ProcessPdfResponse {
  success: boolean;
  data: Record<string, any>;
}

export async function processPdf(file: File): Promise<ProcessPdfResponse> {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await api.post<ProcessPdfResponse>(
      "/api/pdf/process",
      formData,
      {
        isFormData: true, // Tell the API client this is a FormData request
      }
    );

    return response;
  } catch (error) {
    if (error instanceof Error && error.message === "Not authenticated") {
      throw new Error("Please sign in to process PDF files");
    }
    console.error("Error processing PDF:", error);
    throw new Error("Failed to process PDF");
  }
}
