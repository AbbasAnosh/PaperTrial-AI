import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { useAuth } from "@/hooks/useAuth";
import { DS160Form } from "@/components/DS160Form";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Settings,
  FileCheck,
  Globe,
  FileText,
  CreditCard,
  Upload,
} from "lucide-react";
import { FormTemplate } from "@/types/form-template";
import { FormCatalog } from "@/components/form/FormCatalog";
import { DynamicForm } from "@/components/form/DynamicForm";
import { FormGuidance } from "@/components/form/FormGuidance";
import { FileUpload } from "@/components/form/FileUpload";

const Forms = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  const [selectedTemplate, setSelectedTemplate] = useState<FormTemplate | null>(
    null
  );
  const [formMode, setFormMode] = useState<
    "catalog" | "custom" | "application" | "upload"
  >("catalog");
  const [extractedFields, setExtractedFields] = useState<any>(null);

  const handleSelectTemplate = (template: FormTemplate) => {
    setSelectedTemplate(template);
    setFormMode("custom");

    toast({
      title: "Form Selected",
      description: `You're starting the ${template.name} form.`,
    });
  };

  const handleFormComplete = (formData: Record<string, any>) => {
    toast({
      title: "Form Completed",
      description: "Your form has been successfully submitted.",
    });
    setFormMode("catalog");
    setSelectedTemplate(null);
  };

  const handleStartForm = (formId: string) => {
    if (formId === "ds160") {
      setFormMode("application");
      toast({
        title: "Form Selected",
        description: "You're starting the DS-160 visa application form.",
      });
    } else {
      toast({
        title: "Coming Soon",
        description: "This form will be available soon.",
      });
    }
  };

  const handleFileProcessed = (data: any) => {
    setExtractedFields(data);
    setFormMode("custom");
    // You might want to create a template from the extracted fields
    setSelectedTemplate({
      id: "extracted",
      name: "Extracted Form",
      type: "CUSTOM",
      fields: data.fields || [],
    });
  };

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <main className="flex-1 p-6">
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center">
              <SidebarTrigger />
              <h1 className="text-2xl font-bold ml-2">Form Center</h1>
            </div>
            {user && (
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  onClick={() => navigate("/form-admin")}
                >
                  <Settings className="h-4 w-4 mr-2" />
                  Manage Templates
                </Button>
              </div>
            )}
          </div>

          <Tabs
            value={formMode}
            onValueChange={(value: any) => {
              if (value === "catalog") {
                setSelectedTemplate(null);
                setExtractedFields(null);
              }
              setFormMode(value);
            }}
            className="max-w-4xl mx-auto"
          >
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="catalog">Form Catalog</TabsTrigger>
              <TabsTrigger value="upload">Upload PDF</TabsTrigger>
              <TabsTrigger value="application">Legacy DS-160</TabsTrigger>
              {selectedTemplate && (
                <TabsTrigger value="custom">
                  {selectedTemplate.name}
                </TabsTrigger>
              )}
            </TabsList>

            <TabsContent value="catalog" className="mt-6">
              <FormCatalog onSelectTemplate={handleSelectTemplate} />
            </TabsContent>

            <TabsContent value="upload" className="mt-6">
              <FileUpload
                onFileProcessed={handleFileProcessed}
                onError={(error) => {
                  toast({
                    title: "Error",
                    description: error,
                    variant: "destructive",
                  });
                }}
              />
            </TabsContent>

            <TabsContent value="application" className="mt-6">
              <DS160Form />
            </TabsContent>

            <TabsContent value="custom" className="mt-6">
              {selectedTemplate && (
                <DynamicForm
                  template={selectedTemplate}
                  onComplete={handleFormComplete}
                  initialData={extractedFields?.data}
                />
              )}
            </TabsContent>
          </Tabs>
        </main>
      </div>
    </SidebarProvider>
  );
};

export default Forms;
