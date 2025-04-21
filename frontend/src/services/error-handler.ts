import { toast } from "react-hot-toast";
import { AxiosError } from "axios";

interface ApiError {
  message: string;
  code?: string;
  details?: any;
}

class ErrorHandler {
  private static instance: ErrorHandler;
  private constructor() {}

  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler();
    }
    return ErrorHandler.instance;
  }

  handleError(error: unknown): void {
    if (error instanceof AxiosError) {
      this.handleAxiosError(error);
    } else if (error instanceof Error) {
      this.handleGenericError(error);
    } else {
      this.handleUnknownError(error);
    }
  }

  private handleAxiosError(error: AxiosError<ApiError>): void {
    const status = error.response?.status;
    const message = error.response?.data?.message || error.message;

    switch (status) {
      case 400:
        toast.error(`Bad Request: ${message}`);
        break;
      case 401:
        toast.error("Unauthorized: Please log in again");
        // TODO: Handle logout/redirect to login
        break;
      case 403:
        toast.error(
          "Forbidden: You do not have permission to perform this action"
        );
        break;
      case 404:
        toast.error(`Not Found: ${message}`);
        break;
      case 422:
        toast.error(`Validation Error: ${message}`);
        break;
      case 429:
        toast.error("Too many requests. Please try again later");
        break;
      case 500:
        toast.error("Server Error: Please try again later");
        break;
      default:
        toast.error(`Error: ${message}`);
    }

    console.error("API Error:", {
      status,
      message,
      details: error.response?.data?.details,
      url: error.config?.url,
      method: error.config?.method,
    });
  }

  private handleGenericError(error: Error): void {
    toast.error(`Error: ${error.message}`);
    console.error("Generic Error:", error);
  }

  private handleUnknownError(error: unknown): void {
    const message =
      error instanceof Error ? error.message : "An unknown error occurred";
    toast.error(`Unexpected Error: ${message}`);
    console.error("Unknown Error:", error);
  }
}

export const errorHandler = ErrorHandler.getInstance();
