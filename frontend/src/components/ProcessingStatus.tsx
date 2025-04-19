
import { CircleIcon, CheckCircleIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Step {
  name: string;
  status: 'upcoming' | 'current' | 'completed';
}

const steps: Step[] = [
  { name: 'Document Upload', status: 'completed' },
  { name: 'Processing', status: 'current' },
  { name: 'Form Generation', status: 'upcoming' },
  { name: 'Review & Submit', status: 'upcoming' },
];

export function ProcessingStatus() {
  return (
    <div className="w-full max-w-2xl mx-auto mt-8">
      <nav aria-label="Progress">
        <ol role="list" className="space-y-4 md:flex md:space-x-8 md:space-y-0">
          {steps.map((step, stepIdx) => (
            <li key={step.name} className="md:flex-1">
              <div className={cn(
                "group flex flex-col border-l-4 py-2 pl-4 md:border-l-0 md:border-t-4 md:pb-0 md:pl-0 md:pt-4",
                step.status === 'upcoming' ? "border-gray-200" :
                step.status === 'current' ? "border-blue-600" :
                "border-green-600"
              )}>
                <span className="text-sm font-medium">
                  {step.status === 'completed' ? (
                    <CheckCircleIcon className="h-5 w-5 text-green-600" />
                  ) : (
                    <CircleIcon className={cn(
                      "h-5 w-5",
                      step.status === 'current' ? "text-blue-600" : "text-gray-400"
                    )} />
                  )}
                </span>
                <span className={cn(
                  "text-sm font-medium",
                  step.status === 'upcoming' ? "text-gray-500" :
                  step.status === 'current' ? "text-blue-600" :
                  "text-green-600"
                )}>
                  {step.name}
                </span>
              </div>
            </li>
          ))}
        </ol>
      </nav>
    </div>
  );
}
