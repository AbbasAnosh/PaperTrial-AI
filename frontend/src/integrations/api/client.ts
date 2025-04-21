import { supabase } from "@/integrations/supabase/client";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface ApiClientOptions {
  headers?: Record<string, string>;
  isFormData?: boolean;
}

class ApiClient {
  private async getAuthHeaders(
    isFormData: boolean = false
  ): Promise<Record<string, string>> {
    // Wait for auth to be ready
    const {
      data: { session },
      error,
    } = await supabase.auth.getSession();

    if (error || !session) {
      throw new Error("Not authenticated");
    }

    // Get the JWT token from the session
    const token = session.access_token;
    if (!token) {
      throw new Error("No access token available");
    }

    const headers: Record<string, string> = {
      // Format as Bearer token
      Authorization: `Bearer ${token}`,
    };

    // Only add Content-Type for non-FormData requests
    if (!isFormData) {
      headers["Content-Type"] = "application/json";
    }

    return headers;
  }

  async get<T>(path: string, options: ApiClientOptions = {}): Promise<T> {
    const headers = {
      ...(await this.getAuthHeaders(options.isFormData)),
      ...options.headers,
    };

    const response = await fetch(`${API_URL}${path}`, {
      method: "GET",
      headers,
      credentials: "include", // Include cookies for session handling
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Not authenticated");
      }
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async post<T>(
    path: string,
    data: any,
    options: ApiClientOptions = {}
  ): Promise<T> {
    const headers = {
      ...(await this.getAuthHeaders(options.isFormData)),
      ...options.headers,
    };

    const response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers,
      body: options.isFormData ? data : JSON.stringify(data),
      credentials: "include", // Include cookies for session handling
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Not authenticated");
      }
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async put<T>(
    path: string,
    data: any,
    options: ApiClientOptions = {}
  ): Promise<T> {
    const headers = {
      ...(await this.getAuthHeaders(options.isFormData)),
      ...options.headers,
    };

    const response = await fetch(`${API_URL}${path}`, {
      method: "PUT",
      headers,
      body: options.isFormData ? data : JSON.stringify(data),
      credentials: "include", // Include cookies for session handling
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Not authenticated");
      }
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async delete<T>(path: string, options: ApiClientOptions = {}): Promise<T> {
    const headers = {
      ...(await this.getAuthHeaders(options.isFormData)),
      ...options.headers,
    };

    const response = await fetch(`${API_URL}${path}`, {
      method: "DELETE",
      headers,
      credentials: "include", // Include cookies for session handling
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Not authenticated");
      }
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }
}

export const api = new ApiClient();
