
import { useState, useEffect } from 'react';
import { FormTemplate } from '@/types/form-template';
import { useNavigate } from 'react-router-dom';
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { useAuth } from '@/hooks/useAuth';
import { FormTemplateEditor } from '@/components/form/FormTemplateEditor';
import { Plus, Settings, FilePenLine, ListTodo } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';

const FormAdmin = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  const [templates, setTemplates] = useState<FormTemplate[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<FormTemplate | null>(null);
  const [activeTab, setActiveTab] = useState<string>("templates");

  useEffect(() => {
    fetchTemplates();
  }, [user]);

  const fetchTemplates = async () => {
    if (!user) return;
    
    try {
      // Using any to work around the TypeScript issue
      const { data, error } = await supabase
        .from('form_templates' as any)
        .select('*')
        .eq('user_id', user.id);
        
      if (error) throw error;
      
      if (data) {
        const parsedTemplates = data.map((template: any) => ({
          ...template,
          steps: typeof template.steps === 'string' ? JSON.parse(template.steps) : template.steps,
          guidance: typeof template.guidance === 'string' ? JSON.parse(template.guidance) : template.guidance
        }));
        
        setTemplates(parsedTemplates);
      }
    } catch (error) {
      console.error('Error fetching templates:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Could not fetch templates. Please try again later."
      });
    }
  };

  const handleSaveTemplate = (template: FormTemplate) => {
    fetchTemplates();
    setIsCreating(false);
    setEditingTemplate(null);
    setActiveTab("templates");
  };

  const handleDeleteTemplate = async (templateId: string) => {
    if (!user) return;
    
    if (!window.confirm('Are you sure you want to delete this template?')) {
      return;
    }
    
    try {
      // Using any to work around the TypeScript issue
      const { error } = await supabase
        .from('form_templates' as any)
        .delete()
        .eq('id', templateId)
        .eq('user_id', user.id);
        
      if (error) throw error;
      
      fetchTemplates();
      
      toast({
        title: "Template Deleted",
        description: "The form template has been deleted successfully."
      });
    } catch (error) {
      console.error('Error deleting template:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Could not delete template. Please try again later."
      });
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString();
    } catch (e) {
      return 'Invalid date';
    }
  };

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <main className="flex-1 p-6">
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center">
              <SidebarTrigger />
              <h1 className="text-2xl font-bold ml-2">Form Administration</h1>
            </div>
            <Button onClick={() => navigate('/forms')}>
              Back to Forms
            </Button>
          </div>
          
          <Tabs 
            value={activeTab} 
            onValueChange={setActiveTab}
            className="max-w-6xl mx-auto"
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="templates">
                <ListTodo className="mr-2 h-4 w-4" />
                Form Templates
              </TabsTrigger>
              <TabsTrigger value="create">
                <Plus className="mr-2 h-4 w-4" />
                Create Template
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="templates" className="mt-6">
              {templates.length === 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle>No Templates</CardTitle>
                    <CardDescription>
                      You haven't created any form templates yet.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button onClick={() => setActiveTab("create")}>
                      <Plus className="mr-2 h-4 w-4" />
                      Create Your First Template
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-4">
                  {templates.map(template => (
                    <Card key={template.id} className="overflow-hidden">
                      <div className="flex flex-col md:flex-row">
                        <div className="flex-1 p-4">
                          <div className="flex items-start justify-between">
                            <div>
                              <h3 className="font-semibold text-lg">{template.name}</h3>
                              <p className="text-sm text-muted-foreground mb-2">
                                {template.description}
                              </p>
                              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                                <span>Category: {template.category}</span>
                                <span>Country: {template.country}</span>
                                <span>Updated: {formatDate(template.updatedAt)}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                        <div className="p-4 flex items-center space-x-2 border-t md:border-t-0 md:border-l bg-muted/30">
                          <Button 
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setEditingTemplate(template);
                              setActiveTab("create");
                            }}
                          >
                            <FilePenLine className="mr-2 h-4 w-4" />
                            Edit
                          </Button>
                          <Button 
                            variant="outline"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                            onClick={() => handleDeleteTemplate(template.id)}
                          >
                            Delete
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>
            
            <TabsContent value="create" className="mt-6">
              {editingTemplate ? (
                <>
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold">
                      Edit Template: {editingTemplate.name}
                    </h2>
                    <Button 
                      variant="outline" 
                      onClick={() => {
                        setEditingTemplate(null);
                        setActiveTab("templates");
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                  <FormTemplateEditor 
                    onSave={handleSaveTemplate}
                    existingTemplate={editingTemplate}
                  />
                </>
              ) : (
                <>
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold">Create New Template</h2>
                    {isCreating && (
                      <Button 
                        variant="outline" 
                        onClick={() => {
                          setIsCreating(false);
                          setActiveTab("templates");
                        }}
                      >
                        Cancel
                      </Button>
                    )}
                  </div>
                  <FormTemplateEditor onSave={handleSaveTemplate} />
                </>
              )}
            </TabsContent>
          </Tabs>
        </main>
      </div>
    </SidebarProvider>
  );
};

export default FormAdmin;
