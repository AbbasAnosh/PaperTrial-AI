import api from "./api";

export interface FormField {
  id: string;
  name: string;
  type: string;
  page: number;
  confidence: number;
  required: boolean;
}

export interface FormData {
  id: string;
  fields: FormField[];
  created_at: string;
}

export const formsService = {
  async uploadPDF(file: File, onProgress?: (progress: number) => void) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post("/api/v1/forms/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(progress);
        }
      },
    });
    return response.data;
  },

  async processWebForm(url: string) {
    const response = await api.post("/api/v1/forms/process-web", { url });
    return response.data;
  },

  async getFormData(formId: string): Promise<FormData> {
    const response = await api.get(`/api/v1/forms/${formId}`);
    return response.data;
  },

  async updateField(formId: string, fieldId: string, data: Partial<FormField>) {
    const response = await api.patch(
      `/api/v1/forms/${formId}/fields/${fieldId}`,
      data
    );
    return response.data;
  },

  async submitForm(formId: string, answers: Record<string, string>) {
    const response = await api.post(`/api/v1/forms/${formId}/submit`, {
      answers,
    });
    return response.data;
  },
};
