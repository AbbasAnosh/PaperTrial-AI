
import { ChevronLeft, ChevronRight, Camera, Save } from 'lucide-react';
import { Button } from "@/components/ui/button";

interface FormNavigationProps {
  currentStep: number;
  totalSteps: number;
  isSubmitting: boolean;
  savedProgress: boolean;
  onPrevious: () => void;
  onNext: () => void;
  onSave: () => void;
  onScreenshot: () => void;
}

export function FormNavigation({
  currentStep,
  totalSteps,
  isSubmitting,
  savedProgress,
  onPrevious,
  onNext,
  onSave,
  onScreenshot
}: FormNavigationProps) {
  return (
    <div className="flex justify-between border-t p-4">
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={onPrevious}
          disabled={currentStep === 0 || isSubmitting}
        >
          <ChevronLeft className="mr-2 h-4 w-4" />
          Previous
        </Button>
        
        <Button
          variant="outline"
          onClick={onScreenshot}
          disabled={isSubmitting}
        >
          <Camera className="mr-2 h-4 w-4" />
          Capture
        </Button>
      </div>
      
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={onSave}
          disabled={isSubmitting || savedProgress}
        >
          <Save className="mr-2 h-4 w-4" />
          Save Progress
        </Button>
        
        <Button
          onClick={onNext}
          disabled={isSubmitting}
        >
          {currentStep < totalSteps - 1 ? (
            <>
              Next
              <ChevronRight className="ml-2 h-4 w-4" />
            </>
          ) : (
            'Complete'
          )}
        </Button>
      </div>
    </div>
  );
}
