
export interface FormProgress {
  id: string;
  user_id: string;
  form_id: string;
  form_data: Record<string, any>;
  screenshots: string[];
  last_step_index: number;
  created_at: string;
  updated_at: string;
}
