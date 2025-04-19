
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from '@/components/ui/button';

interface FormErrorDisplayProps {
  hasError: boolean;
  retryCount?: number;
  onRetry?: () => void;
}

export function FormErrorDisplay({ hasError, retryCount = 0, onRetry }: FormErrorDisplayProps) {
  if (!hasError) return null;
  
  return (
    <Alert variant="destructive" className="mb-4">
      <div className="flex justify-between items-start">
        <div className="flex">
          <AlertTriangle className="h-4 w-4 mt-0.5" />
          <div className="ml-2">
            <AlertTitle>Submission Error</AlertTitle>
            <AlertDescription>
              {retryCount > 0 ? (
                <>
                  We've tried {retryCount} time{retryCount !== 1 ? 's' : ''} to submit your form.
                  {onRetry ? ' You can retry manually or we will try again automatically.' : ' We will try again automatically.'}
                </>
              ) : (
                'There was a problem submitting the form. We\'ll try again or you can retry manually.'
              )}
            </AlertDescription>
          </div>
        </div>
        
        {onRetry && (
          <Button 
            variant="outline" 
            size="sm" 
            className="shrink-0 mt-1"
            onClick={onRetry}
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1" />
            Retry Now
          </Button>
        )}
      </div>
    </Alert>
  );
}
