import { useState } from 'react';
import { FormTemplate, FormStep, FormField } from '@/types/form-template';
import { useForm } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Form, FormControl, FormDescription, FormField as HookFormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { X, Plus, AlertTriangle, Save, TrashIcon } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';

export function FormTemplateEditor({ onSave, existingTemplate }: { 
  onSave: (template: FormTemplate) => void,
  existingTemplate?: FormTemplate 
}) {
  const [template, setTemplate] = useState<FormTemplate>(existingTemplate || {
    id: `template-${Date.now()}`,
    name: '',
    description: '',
    country: '',
    category: '',
    steps: [],
    guidance: {
      introduction: '',
      requiredDocuments: [],
      processingTime: '',
      fees: '',
      additionalInfo: ''
    },
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  });
  
  const [newDocumentItem, setNewDocumentItem] = useState('');
  const [currentStep, setCurrentStep] = useState<number | null>(null);
  const [currentField, setCurrentField] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();
  const { user } = useAuth();

  const updateTemplate = (updates: Partial<FormTemplate>) => {
    setTemplate(prev => ({
      ...prev,
      ...updates,
      updatedAt: new Date().toISOString()
    }));
  };

  const addStep = () => {
    const newStep: FormStep = {
      id: `step-${Date.now()}`,
      title: `Step ${template.steps.length + 1}`,
      description: '',
      fields: []
    };
    
    updateTemplate({
      steps: [...template.steps, newStep]
    });
    
    setCurrentStep(template.steps.length);
  };

  const updateStep = (index: number, updates: Partial<FormStep>) => {
    const steps = [...template.steps];
    steps[index] = { ...steps[index], ...updates };
    updateTemplate({ steps });
  };

  const removeStep = (index: number) => {
    const steps = template.steps.filter((_, i) => i !== index);
    updateTemplate({ steps });
    setCurrentStep(null);
  };

  const addField = (stepIndex: number) => {
    const steps = [...template.steps];
    const newField: FormField = {
      id: `field-${Date.now()}`,
      name: `field_${Date.now()}`,
      label: 'New Field',
      type: 'text',
      required: false
    };
    
    steps[stepIndex].fields = [...steps[stepIndex].fields, newField];
    updateTemplate({ steps });
    setCurrentField(steps[stepIndex].fields.length - 1);
  };

  const updateField = (stepIndex: number, fieldIndex: number, updates: Partial<FormField>) => {
    const steps = [...template.steps];
    steps[stepIndex].fields[fieldIndex] = { 
      ...steps[stepIndex].fields[fieldIndex], 
      ...updates 
    };
    updateTemplate({ steps });
  };

  const removeField = (stepIndex: number, fieldIndex: number) => {
    const steps = [...template.steps];
    steps[stepIndex].fields = steps[stepIndex].fields.filter((_, i) => i !== fieldIndex);
    updateTemplate({ steps });
    setCurrentField(null);
  };

  const addRequiredDocument = () => {
    if (!newDocumentItem.trim()) return;
    
    const guidance = { ...template.guidance };
    guidance.requiredDocuments = [...(guidance.requiredDocuments || []), newDocumentItem.trim()];
    
    updateTemplate({ guidance });
    setNewDocumentItem('');
  };

  const removeRequiredDocument = (index: number) => {
    const guidance = { ...template.guidance };
    guidance.requiredDocuments = guidance.requiredDocuments?.filter((_, i) => i !== index) || [];
    updateTemplate({ guidance });
  };

  const handleSave = async () => {
    if (!template.name.trim()) {
      toast({
        variant: "destructive",
        title: "Missing Information",
        description: "Template name is required."
      });
      return;
    }

    setSaving(true);
    
    try {
      if (user) {
        const { error } = await supabase
          .from('form_templates' as any)
          .upsert({
            id: template.id,
            name: template.name,
            description: template.description,
            country: template.country,
            category: template.category,
            steps: JSON.stringify(template.steps),
            guidance: JSON.stringify(template.guidance),
            created_at: template.createdAt,
            updated_at: new Date().toISOString(),
            user_id: user.id
          });
          
        if (error) throw error;
      }
      
      onSave(template);
      
      toast({
        title: "Template Saved",
        description: "Your form template has been saved successfully."
      });
    } catch (error) {
      console.error('Error saving template:', error);
      toast({
        variant: "destructive",
        title: "Save Failed",
        description: "There was an error saving your template. Please try again."
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <Tabs defaultValue="basic">
        <TabsList className="grid grid-cols-3 mb-6">
          <TabsTrigger value="basic">Basic Information</TabsTrigger>
          <TabsTrigger value="steps">Form Steps</TabsTrigger>
          <TabsTrigger value="guidance">Guidance</TabsTrigger>
        </TabsList>
        
        <TabsContent value="basic">
          <Card>
            <CardHeader>
              <CardTitle>Template Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="template-name">Template Name</Label>
                <Input 
                  id="template-name"
                  value={template.name} 
                  onChange={(e) => updateTemplate({ name: e.target.value })}
                  placeholder="e.g., DS-160 Visa Application"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="template-description">Description</Label>
                <Textarea 
                  id="template-description"
                  value={template.description} 
                  onChange={(e) => updateTemplate({ description: e.target.value })}
                  placeholder="Describe what this form is used for"
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="template-country">Country</Label>
                  <Input 
                    id="template-country"
                    value={template.country} 
                    onChange={(e) => updateTemplate({ country: e.target.value })}
                    placeholder="e.g., United States"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="template-category">Category</Label>
                  <Select 
                    value={template.category} 
                    onValueChange={(value) => updateTemplate({ category: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Immigration">Immigration</SelectItem>
                      <SelectItem value="Business">Business</SelectItem>
                      <SelectItem value="Education">Education</SelectItem>
                      <SelectItem value="Employment">Employment</SelectItem>
                      <SelectItem value="Tax">Tax</SelectItem>
                      <SelectItem value="Legal">Legal</SelectItem>
                      <SelectItem value="Other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="steps">
          <div className="flex flex-col-reverse md:flex-row gap-6">
            <div className="flex-1">
              <Card className="mb-4">
                <CardHeader>
                  <CardTitle>Form Steps</CardTitle>
                </CardHeader>
                <CardContent>
                  {template.steps.length === 0 ? (
                    <div className="text-center py-8 border rounded-lg bg-muted/20">
                      <p className="text-muted-foreground mb-4">No steps added yet</p>
                      <Button onClick={addStep}>Add First Step</Button>
                    </div>
                  ) : (
                    <Accordion 
                      type="single" 
                      collapsible 
                      value={currentStep !== null ? `step-${currentStep}` : undefined}
                      onValueChange={(value) => setCurrentStep(value ? parseInt(value.split('-')[1]) : null)}
                    >
                      {template.steps.map((step, index) => (
                        <AccordionItem key={step.id} value={`step-${index}`}>
                          <div className="flex items-center justify-between">
                            <AccordionTrigger className="flex-1">
                              {step.title || `Step ${index + 1}`}
                            </AccordionTrigger>
                            <Button 
                              variant="ghost" 
                              size="icon"
                              className="h-8 w-8"
                              onClick={(e) => {
                                e.stopPropagation();
                                removeStep(index);
                              }}
                            >
                              <TrashIcon className="h-4 w-4" />
                            </Button>
                          </div>
                          <AccordionContent>
                            <div className="space-y-4 pt-2">
                              <div className="space-y-2">
                                <Label htmlFor={`step-title-${index}`}>Step Title</Label>
                                <Input 
                                  id={`step-title-${index}`}
                                  value={step.title} 
                                  onChange={(e) => updateStep(index, { title: e.target.value })}
                                />
                              </div>
                              
                              <div className="space-y-2">
                                <Label htmlFor={`step-description-${index}`}>Description</Label>
                                <Textarea 
                                  id={`step-description-${index}`}
                                  value={step.description} 
                                  onChange={(e) => updateStep(index, { description: e.target.value })}
                                />
                              </div>
                              
                              <div className="space-y-2">
                                <Label htmlFor={`step-condition-${index}`}>Condition (optional)</Label>
                                <Input 
                                  id={`step-condition-${index}`}
                                  value={step.condition || ''} 
                                  onChange={(e) => updateStep(index, { condition: e.target.value })}
                                  placeholder="e.g., formData.needsVisa === true"
                                />
                                <p className="text-xs text-muted-foreground">
                                  A JavaScript condition that determines whether this step should be shown.
                                </p>
                              </div>
                              
                              <div className="space-y-2 pt-4">
                                <div className="flex items-center justify-between mb-2">
                                  <Label>Fields</Label>
                                  <Button 
                                    size="sm" 
                                    variant="outline" 
                                    onClick={() => addField(index)}
                                  >
                                    <Plus className="h-4 w-4 mr-1" /> Add Field
                                  </Button>
                                </div>
                                
                                {step.fields.length === 0 ? (
                                  <div className="text-center p-4 border rounded-md bg-muted/10">
                                    <p className="text-sm text-muted-foreground">No fields added yet</p>
                                  </div>
                                ) : (
                                  <div className="space-y-3">
                                    {step.fields.map((field, fieldIndex) => (
                                      <div 
                                        key={field.id} 
                                        className={`p-3 border rounded-md ${currentField === fieldIndex ? 'border-primary' : ''}`}
                                      >
                                        <div className="flex items-center justify-between mb-2">
                                          <h4 className="font-medium">{field.label}</h4>
                                          <div className="flex gap-1">
                                            <Button 
                                              variant="ghost" 
                                              size="icon" 
                                              className="h-6 w-6"
                                              onClick={() => setCurrentField(currentField === fieldIndex ? null : fieldIndex)}
                                            >
                                              {currentField === fieldIndex ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                                            </Button>
                                            <Button 
                                              variant="ghost" 
                                              size="icon" 
                                              className="h-6 w-6"
                                              onClick={() => removeField(index, fieldIndex)}
                                            >
                                              <TrashIcon className="h-4 w-4" />
                                            </Button>
                                          </div>
                                        </div>
                                        
                                        {currentField === fieldIndex && (
                                          <div className="space-y-3 pt-2">
                                            <div className="grid grid-cols-2 gap-3">
                                              <div className="space-y-1">
                                                <Label htmlFor={`field-label-${fieldIndex}`} className="text-xs">Label</Label>
                                                <Input 
                                                  id={`field-label-${fieldIndex}`}
                                                  size="sm"
                                                  value={field.label} 
                                                  onChange={(e) => updateField(index, fieldIndex, { label: e.target.value })}
                                                />
                                              </div>
                                              <div className="space-y-1">
                                                <Label htmlFor={`field-name-${fieldIndex}`} className="text-xs">Field Name</Label>
                                                <Input 
                                                  id={`field-name-${fieldIndex}`}
                                                  size="sm"
                                                  value={field.name} 
                                                  onChange={(e) => updateField(index, fieldIndex, { name: e.target.value })}
                                                />
                                              </div>
                                            </div>
                                            
                                            <div className="grid grid-cols-2 gap-3">
                                              <div className="space-y-1">
                                                <Label htmlFor={`field-type-${fieldIndex}`} className="text-xs">Field Type</Label>
                                                <Select 
                                                  value={field.type} 
                                                  onValueChange={(value: any) => updateField(index, fieldIndex, { type: value })}
                                                >
                                                  <SelectTrigger id={`field-type-${fieldIndex}`}>
                                                    <SelectValue />
                                                  </SelectTrigger>
                                                  <SelectContent>
                                                    <SelectItem value="text">Text</SelectItem>
                                                    <SelectItem value="number">Number</SelectItem>
                                                    <SelectItem value="select">Select</SelectItem>
                                                    <SelectItem value="date">Date</SelectItem>
                                                    <SelectItem value="textarea">Textarea</SelectItem>
                                                    <SelectItem value="checkbox">Checkbox</SelectItem>
                                                  </SelectContent>
                                                </Select>
                                              </div>
                                              <div className="space-y-1 flex items-end">
                                                <div className="flex items-center space-x-2">
                                                  <input
                                                    type="checkbox"
                                                    id={`field-required-${fieldIndex}`}
                                                    checked={field.required}
                                                    onChange={(e) => updateField(index, fieldIndex, { required: e.target.checked })}
                                                    className="h-4 w-4"
                                                  />
                                                  <Label htmlFor={`field-required-${fieldIndex}`} className="text-xs">Required</Label>
                                                </div>
                                              </div>
                                            </div>
                                            
                                            <div className="space-y-1">
                                              <Label htmlFor={`field-placeholder-${fieldIndex}`} className="text-xs">Placeholder</Label>
                                              <Input 
                                                id={`field-placeholder-${fieldIndex}`}
                                                size="sm"
                                                value={field.placeholder || ""} 
                                                onChange={(e) => updateField(index, fieldIndex, { placeholder: e.target.value })}
                                              />
                                            </div>
                                            
                                            <div className="space-y-1">
                                              <Label htmlFor={`field-help-${fieldIndex}`} className="text-xs">Help Text</Label>
                                              <Input 
                                                id={`field-help-${fieldIndex}`}
                                                size="sm"
                                                value={field.helpText || ""} 
                                                onChange={(e) => updateField(index, fieldIndex, { helpText: e.target.value })}
                                              />
                                            </div>
                                            
                                            {field.type === 'select' && (
                                              <div className="space-y-2 pt-1">
                                                <Label className="text-xs">Options</Label>
                                                <div className="space-y-2">
                                                  {(field.options || []).map((option, optionIndex) => (
                                                    <div key={optionIndex} className="flex gap-2">
                                                      <Input 
                                                        placeholder="Value"
                                                        value={option.value}
                                                        onChange={(e) => {
                                                          const options = [...(field.options || [])];
                                                          options[optionIndex].value = e.target.value;
                                                          updateField(index, fieldIndex, { options });
                                                        }}
                                                        className="flex-1"
                                                      />
                                                      <Input 
                                                        placeholder="Label"
                                                        value={option.label}
                                                        onChange={(e) => {
                                                          const options = [...(field.options || [])];
                                                          options[optionIndex].label = e.target.value;
                                                          updateField(index, fieldIndex, { options });
                                                        }}
                                                        className="flex-1"
                                                      />
                                                      <Button 
                                                        variant="ghost" 
                                                        size="icon" 
                                                        onClick={() => {
                                                          const options = (field.options || []).filter((_, i) => i !== optionIndex);
                                                          updateField(index, fieldIndex, { options });
                                                        }}
                                                      >
                                                        <X className="h-4 w-4" />
                                                      </Button>
                                                    </div>
                                                  ))}
                                                  <Button 
                                                    variant="outline" 
                                                    size="sm" 
                                                    className="w-full"
                                                    onClick={() => {
                                                      const options = [...(field.options || []), { value: '', label: '' }];
                                                      updateField(index, fieldIndex, { options });
                                                    }}
                                                  >
                                                    Add Option
                                                  </Button>
                                                </div>
                                              </div>
                                            )}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      ))}
                    </Accordion>
                  )}
                </CardContent>
                <CardFooter>
                  <Button onClick={addStep} className="w-full">
                    <Plus className="h-4 w-4 mr-2" /> Add Step
                  </Button>
                </CardFooter>
              </Card>
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="guidance">
          <Card>
            <CardHeader>
              <CardTitle>Guidance Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="guidance-intro">Introduction</Label>
                <Textarea 
                  id="guidance-intro"
                  value={template.guidance?.introduction || ''} 
                  onChange={(e) => updateTemplate({ 
                    guidance: { ...template.guidance, introduction: e.target.value } 
                  })}
                  placeholder="Explain what this form is for and when it should be used"
                  className="min-h-[100px]"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Required Documents</Label>
                <div className="flex gap-2 mb-2">
                  <Input 
                    value={newDocumentItem} 
                    onChange={(e) => setNewDocumentItem(e.target.value)}
                    placeholder="Add a required document"
                  />
                  <Button 
                    variant="outline" 
                    onClick={addRequiredDocument}
                  >
                    Add
                  </Button>
                </div>
                
                <div className="space-y-2">
                  {(template.guidance?.requiredDocuments || []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No required documents specified</p>
                  ) : (
                    (template.guidance?.requiredDocuments || []).map((doc, index) => (
                      <div key={index} className="flex items-center justify-between p-2 border rounded-md">
                        <span>{doc}</span>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8"
                          onClick={() => removeRequiredDocument(index)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="processing-time">Processing Time</Label>
                  <Input 
                    id="processing-time"
                    value={template.guidance?.processingTime || ''} 
                    onChange={(e) => updateTemplate({ 
                      guidance: { ...template.guidance, processingTime: e.target.value } 
                    })}
                    placeholder="e.g., 2-3 weeks"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="fees">Fees</Label>
                  <Input 
                    id="fees"
                    value={template.guidance?.fees || ''} 
                    onChange={(e) => updateTemplate({ 
                      guidance: { ...template.guidance, fees: e.target.value } 
                    })}
                    placeholder="e.g., $100 USD"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="additional-info">Additional Information</Label>
                <Textarea 
                  id="additional-info"
                  value={template.guidance?.additionalInfo || ''} 
                  onChange={(e) => updateTemplate({ 
                    guidance: { ...template.guidance, additionalInfo: e.target.value } 
                  })}
                  placeholder="Any other important details about this form"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      
      <div className="flex justify-end mt-6">
        <Button 
          onClick={handleSave} 
          disabled={saving}
          className="w-full md:w-auto"
        >
          {saving ? 'Saving...' : 'Save Template'}
        </Button>
      </div>
    </div>
  );
}
