import { supabase } from "../integrations/supabase/client";
import { toast } from "react-hot-toast";

export interface User {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
}

export interface AuthResponse {
  user: User | null;
  error: Error | null;
}

export const supabaseService = {
  async signUp(
    email: string,
    password: string,
    fullName: string
  ): Promise<AuthResponse> {
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
          },
        },
      });

      if (error) throw error;

      return {
        user: data.user as User,
        error: null,
      };
    } catch (error) {
      toast.error("Failed to sign up. Please try again.");
      return {
        user: null,
        error: error as Error,
      };
    }
  },

  async signIn(email: string, password: string): Promise<AuthResponse> {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) throw error;

      return {
        user: data.user as User,
        error: null,
      };
    } catch (error) {
      toast.error("Invalid email or password");
      return {
        user: null,
        error: error as Error,
      };
    }
  },

  async signOut(): Promise<void> {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      toast.success("Signed out successfully");
    } catch (error) {
      toast.error("Failed to sign out");
      throw error;
    }
  },

  async getCurrentUser(): Promise<User | null> {
    try {
      const {
        data: { user },
        error,
      } = await supabase.auth.getUser();
      if (error) throw error;
      return user as User;
    } catch (error) {
      console.error("Error getting current user:", error);
      return null;
    }
  },

  async updateProfile(
    userId: string,
    updates: Partial<User>
  ): Promise<AuthResponse> {
    try {
      const { data, error } = await supabase
        .from("profiles")
        .update(updates)
        .eq("id", userId)
        .select()
        .single();

      if (error) throw error;

      return {
        user: data as User,
        error: null,
      };
    } catch (error) {
      toast.error("Failed to update profile");
      return {
        user: null,
        error: error as Error,
      };
    }
  },
};
