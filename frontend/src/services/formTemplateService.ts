import { supabase } from "@/integrations/supabase/client";
import { FormTemplate, FormField, FormGuidance } from "@/types/form";

export interface FormGuidance {
  id: string;
  formId: string;
  step: number;
  content: string;
  tips: string[];
  commonMistakes: string[];
  estimatedTime: string;
  requiredDocuments: string[];
}

export class FormTemplateService {
  static async getFormCatalog(): Promise<FormTemplate[]> {
    const { data, error } = await supabase
      .from("form_templates")
      .select("*")
      .order("name");

    if (error) throw error;
    return data || [];
  }

  static async getFormTemplate(formId: string): Promise<FormTemplate> {
    const { data, error } = await supabase
      .from("form_templates")
      .select("*")
      .eq("id", formId)
      .single();

    if (error) throw error;
    return data;
  }

  static async getFormGuidance(formId: string): Promise<FormGuidance[]> {
    const { data, error } = await supabase
      .from("form_guidance")
      .select("*")
      .eq("form_id", formId)
      .order("step");

    if (error) throw error;
    return data || [];
  }

  static async createFormTemplate(
    template: Omit<FormTemplate, "id">
  ): Promise<FormTemplate> {
    const { data, error } = await supabase
      .from("form_templates")
      .insert(template)
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  static async updateFormTemplate(
    formId: string,
    updates: Partial<FormTemplate>
  ): Promise<FormTemplate> {
    const { data, error } = await supabase
      .from("form_templates")
      .update(updates)
      .eq("id", formId)
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  static async generateFormGuidance(formId: string): Promise<FormGuidance[]> {
    const { data, error } = await supabase.functions.invoke(
      "generate-guidance",
      {
        body: { formId },
      }
    );

    if (error) throw error;
    return data;
  }

  static async searchForms(query: string): Promise<FormTemplate[]> {
    const { data, error } = await supabase
      .from("form_templates")
      .select("*")
      .or(
        `name.ilike.%${query}%,description.ilike.%${query}%,category.ilike.%${query}%`
      );

    if (error) throw error;
    return data || [];
  }

  static async getFormCategories(): Promise<string[]> {
    try {
      const { data, error } = await supabase
        .from("form_templates")
        .select("category", { count: "exact" })
        .order("category");

      if (error) throw error;
      return data.map((item: any) => item.category);
    } catch (error) {
      console.error("Error fetching form categories:", error);
      throw error;
    }
  }

  static async getFormsByCategory(category: string): Promise<FormTemplate[]> {
    const { data, error } = await supabase
      .from("form_templates")
      .select("*")
      .eq("category", category)
      .order("name");

    if (error) throw error;
    return data || [];
  }

  static async createFormGuidance(
    guidance: FormGuidance
  ): Promise<FormGuidance> {
    const { data, error } = await supabase
      .from("form_guidance")
      .insert([guidance])
      .select()
      .single();

    if (error) throw error;
    return data;
  }
}
