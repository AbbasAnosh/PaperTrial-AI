import React, { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/components/ui/use-toast';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { useAuth } from '@/hooks/useAuth';
import { FormProgress } from './form/FormProgress';
import { FormNavigation } from './form/FormNavigation';
import { ScreenshotGallery } from './form/ScreenshotGallery';
import { FormErrorDisplay } from './form/FormErrorDisplay';

interface FormStep {
  id: string;
  title: string;
  component: React.ReactNode;
  condition?: (formData: Record<string, any>) => boolean;
}

interface MultiStepFormProps {
  formSteps: FormStep[];
  onComplete: (formData: Record<string, any>) => void;
  formId: string;
  initialData?: Record<string, any>;
}

export function MultiStepForm({ formSteps, onComplete, formId, initialData = {} }: MultiStepFormProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [formData, setFormData] = useState<Record<string, any>>(initialData);
  const [screenshots, setScreenshots] = useState<string[]>([]);
  const [retryCount, setRetryCount] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [savedProgress, setSavedProgress] = useState(false);

  const filteredSteps = formSteps.filter(step => 
    !step.condition || step.condition(formData)
  );
  
  const currentStep = filteredSteps[currentStepIndex];
  const progress = ((currentStepIndex + 1) / filteredSteps.length) * 100;

  useEffect(() => {
    const loadSavedProgress = async () => {
      if (!user) return;
      
      try {
        const { data, error } = await supabase
          .from('form_progress')
          .select('*')
          .eq('user_id', user.id)
          .eq('form_id', formId)
          .single();
        
        if (error) {
          console.error('Error loading saved progress:', error);
          return;
        }
        
        if (data) {
          const savedFormData = data.form_data as Record<string, any> || {};
          setFormData(savedFormData);
          
          const savedScreenshots = Array.isArray(data.screenshots) ? data.screenshots : [];
          setScreenshots(savedScreenshots);
          
          const lastStepIndex = Math.min(
            data.last_step_index || 0,
            filteredSteps.length - 1
          );
          setCurrentStepIndex(lastStepIndex);
          setSavedProgress(true);
          
          toast({
            title: "Progress Restored",
            description: "Continuing from where you left off.",
          });
        }
      } catch (error) {
        console.error('Failed to load progress:', error);
      }
    };
    
    loadSavedProgress();
  }, [user, formId, filteredSteps.length]);

  const saveProgress = async () => {
    if (!user) return;
    
    try {
      setIsSubmitting(true);
      
      const { error } = await supabase
        .from('form_progress')
        .upsert({
          user_id: user.id,
          form_id: formId,
          form_data: formData,
          screenshots: screenshots,
          last_step_index: currentStepIndex,
          updated_at: new Date().toISOString()
        }, {
          onConflict: 'user_id,form_id'
        });
      
      if (error) throw error;
      
      setSavedProgress(true);
      toast({
        title: "Progress Saved",
        description: "You can resume this form later.",
      });
    } catch (error) {
      console.error('Error saving progress:', error);
      toast({
        variant: "destructive",
        title: "Save Failed",
        description: "Could not save your progress. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const takeScreenshot = async () => {
    try {
      const timestamp = new Date().toISOString();
      const screenshotId = `screenshot_${timestamp}`;
      
      setScreenshots(prev => [...prev, screenshotId]);
      
      toast({
        title: "Screenshot Captured",
        description: "Form state has been documented.",
      });
    } catch (error) {
      console.error('Error taking screenshot:', error);
      toast({
        variant: "destructive",
        title: "Screenshot Failed",
        description: "Could not capture the current screen.",
      });
    }
  };

  const goToNextStep = async () => {
    if (currentStepIndex < filteredSteps.length - 1) {
      takeScreenshot();
      setCurrentStepIndex(prev => prev + 1);
      setSavedProgress(false);
    } else {
      await handleFormCompletion();
    }
  };

  const goToPreviousStep = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
      setSavedProgress(false);
    }
  };

  const handleFormCompletion = async () => {
    setIsSubmitting(true);
    setHasError(false);
    
    try {
      await submitWithRetry(() => {
        return new Promise((resolve, reject) => {
          const shouldSucceed = Math.random() > 0.3;
          
          setTimeout(() => {
            if (shouldSucceed || retryCount >= 2) {
              resolve({ success: true });
            } else {
              reject(new Error("Submission temporarily failed"));
            }
          }, 1000);
        });
      }, 3);
      
      await takeScreenshot();
      
      onComplete(formData);
      
      if (user) {
        await supabase
          .from('form_progress')
          .delete()
          .eq('user_id', user.id)
          .eq('form_id', formId);
      }
      
      toast({
        title: "Form Completed",
        description: "Your submission was successful!",
      });
    } catch (error) {
      console.error('Form submission failed after retries:', error);
      setHasError(true);
      toast({
        variant: "destructive",
        title: "Submission Failed",
        description: "Please try again or contact support if the problem persists.",
      });
    } finally {
      setIsSubmitting(false);
      setRetryCount(0);
    }
  };

  const submitWithRetry = async (fn: () => Promise<any>, maxRetries: number) => {
    try {
      return await fn();
    } catch (error) {
      if (retryCount >= maxRetries) {
        throw error;
      }
      
      const delay = Math.pow(2, retryCount) * 1000;
      console.log(`Retry ${retryCount + 1}/${maxRetries} after ${delay}ms`);
      
      setRetryCount(prev => prev + 1);
      
      await new Promise(resolve => setTimeout(resolve, delay));
      
      return submitWithRetry(fn, maxRetries);
    }
  };

  const updateFormData = (newData: Record<string, any>) => {
    setFormData(prevData => ({
      ...prevData,
      ...newData
    }));
    setSavedProgress(false);
  };

  const stepProps = {
    formData,
    updateFormData
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <Card className="shadow-lg">
        <CardHeader>
          <FormProgress
            currentStep={currentStepIndex}
            totalSteps={filteredSteps.length}
            title={currentStep.title}
          />
        </CardHeader>
        
        <CardContent>
          <FormErrorDisplay hasError={hasError} />
          
          <div className="py-4">
            {React.isValidElement(currentStep.component)
              ? React.cloneElement(currentStep.component as React.ReactElement, stepProps)
              : currentStep.component}
          </div>
        </CardContent>
        
        <FormNavigation
          currentStep={currentStepIndex}
          totalSteps={filteredSteps.length}
          isSubmitting={isSubmitting}
          savedProgress={savedProgress}
          onPrevious={goToPreviousStep}
          onNext={goToNextStep}
          onSave={saveProgress}
          onScreenshot={takeScreenshot}
        />
      </Card>
      
      <ScreenshotGallery screenshots={screenshots} />
    </div>
  );
}
