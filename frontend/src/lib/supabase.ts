import { createClient } from "@supabase/supabase-js";

// Hardcoded values to ensure the client works
const SUPABASE_URL = "https://jrizrpjpjpqolculmckf.supabase.co";
const SUPABASE_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMFTYT8_I0";

// Create Supabase client with hardcoded values
export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// API URL for other services
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
