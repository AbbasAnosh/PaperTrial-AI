export interface FormField {
  id: string;
  name: string;
  label: string;
  type: string;
  required: boolean;
  options?: string[];
  validation?: {
    pattern?: string;
    min?: number;
    max?: number;
  };
  placeholder?: string;
  helpText?: string;
  coordinates: {
    x: number;
    y: number;
  };
  page: number;
  value?: string;
  confidence?: number;
  cluster?: number;
  relatedFields?: string[];
  validationRules?: {
    required?: boolean;
    pattern?: RegExp;
    minLength?: number;
    maxLength?: number;
  };
  mappedTo?: string;
  mappingConfidence?: number;
  relatedTo?: string;
  inheritedConfidence?: number;
  conditional?: {
    field: string;
    value: any;
    show: boolean;
  };
}

export interface FormStep {
  id: string;
  title: string;
  description?: string;
  fields: FormField[];
}

export interface FormTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  steps: FormStep[];
  estimatedTime: number;
  requiredDocuments: string[];
  fields: FormField[];
  guidance?: FormGuidance;
}

export type FormType =
  | "DS160" // US Visa Application
  | "I485" // Adjustment of Status
  | "N400" // Naturalization
  | "I130" // Petition for Alien Relative
  | "I765" // Work Authorization
  | "I131" // Travel Document
  | "I129" // Worker Petition
  | "I140" // Immigration Petition
  | "I821D" // DACA
  | "I589"; // Asylum

export interface FormProgress {
  id: string;
  formId: string;
  userId: string;
  currentStep: number;
  totalSteps: number;
  completedFields: string[];
  errors: Record<string, string>;
  screenshots: Record<number, string>;
  status: "in_progress" | "completed" | "failed";
  lastError?: string;
  retryCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface FormSubmission {
  id: string;
  formId: string;
  userId: string;
  formData: Record<string, any>;
  screenshots: Record<number, string>;
  status:
    | "queued"
    | "processing"
    | "submitted"
    | "completed"
    | "failed"
    | "cancelled";
  confirmationNumber?: string;
  error?: string;
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, any>;
  documentId?: string;
  responseData?: Record<string, any>;
  retryCount?: number;
  maxRetries?: number;
  lastRetryAt?: string;
  isDeleted?: boolean;
  deletedAt?: string;
}

export interface ProcessedDocument {
  id: string;
  original_filename: string;
  processed_data: Record<string, any>;
  user_id: string;
  created_at: Date;
  form_type: FormType;
}

export interface FormGuidance {
  id: string;
  form_id: string;
  step: number;
  content: string;
  tips: string[];
  common_mistakes: string[];
  required_documents: string[];
  estimated_time: number;
  created_at: string;
  updated_at: string;
  title: string;
  description: string;
  steps: {
    id: string;
    title: string;
    content: string;
  }[];
}
