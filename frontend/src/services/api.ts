import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import { errorHandler } from "./error-handler";
import { supabase } from "../integrations/supabase/client";

class ApiService {
  private static instance: ApiService;
  private api: AxiosInstance;

  private constructor() {
    this.api = axios.create({
      baseURL: "", // Remove the /api prefix from baseURL
      headers: {
        "Content-Type": "application/json",
      },
      timeout: 30000, // 30 seconds timeout
    });

    // Add request interceptor for Supabase auth token
    this.api.interceptors.request.use(async (config) => {
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (session?.access_token) {
          config.headers.Authorization = `Bearer ${session.access_token}`;
        }
        return config;
      } catch (error) {
        console.error("Error getting auth session:", error);
        return config;
      }
    });

    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error("API Error:", {
          status: error.response?.status,
          message: error.message,
          details: error.response?.data,
          url: error.config?.url,
          method: error.config?.method,
        });
        errorHandler.handleError(error);
        return Promise.reject(error);
      }
    );
  }

  static getInstance(): ApiService {
    if (!ApiService.instance) {
      ApiService.instance = new ApiService();
    }
    return ApiService.instance;
  }

  // Form endpoints
  async uploadPDF(file: File, onProgress?: (progress: number) => void) {
    // Validate file type
    if (!file.type || !file.type.toLowerCase().includes("pdf")) {
      throw new Error("Only PDF files are allowed");
    }

    // Create a new File object with the correct MIME type
    const pdfFile = new File([file], file.name, { type: "application/pdf" });

    const formData = new FormData();
    formData.append("file", pdfFile);

    const config: AxiosRequestConfig = {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(progress);
        }
      },
    };

    try {
      const response = await this.api.post(
        "/api/v1/forms/process-pdf",
        formData,
        config
      );
      return response.data;
    } catch (error) {
      console.error("Error uploading PDF:", error);
      throw error;
    }
  }

  async processWebForm(url: string) {
    try {
      const response = await this.api.post("/api/v1/forms/process-web", {
        url,
      });
      return response.data;
    } catch (error) {
      console.error("Error processing web form:", error);
      throw error;
    }
  }

  async getFormFields(formId: string) {
    try {
      const response = await this.api.get(`/api/v1/forms/${formId}`);
      return response.data;
    } catch (error) {
      console.error("Error getting form fields:", error);
      throw error;
    }
  }

  async updateFormField(formId: string, fieldId: string, data: any) {
    try {
      const response = await this.api.patch(
        `/api/v1/forms/${formId}/fields/${fieldId}`,
        data
      );
      return response.data;
    } catch (error) {
      console.error("Error updating form field:", error);
      throw error;
    }
  }

  async submitForm(formId: string, data: any) {
    try {
      const response = await this.api.post(`/api/v1/forms/submissions`, {
        form_id: formId,
        answers: data,
      });
      return response.data;
    } catch (error) {
      console.error("Error submitting form:", error);
      throw error;
    }
  }

  // PDF endpoints
  async getPDFPreview(formId: string) {
    try {
      const response = await this.api.get(`/api/v1/pdf/${formId}/preview`);
      return response.data;
    } catch (error) {
      console.error("Error getting PDF preview:", error);
      throw error;
    }
  }
}

export const apiService = ApiService.getInstance();
