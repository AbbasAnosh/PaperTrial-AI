
import { Progress } from "@/components/ui/progress";

interface FormProgressProps {
  currentStep: number;
  totalSteps: number;
  title: string;
}

export function FormProgress({ currentStep, totalSteps, title }: FormProgressProps) {
  const progress = ((currentStep + 1) / totalSteps) * 100;
  
  return (
    <div className="w-full">
      <div className="flex justify-between mb-2">
        <span>{title}</span>
        <span className="text-sm text-muted-foreground">
          Step {currentStep + 1} of {totalSteps}
        </span>
      </div>
      <Progress value={progress} className="h-2" />
    </div>
  );
}
