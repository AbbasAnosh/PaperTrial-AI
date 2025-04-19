
import { useState } from 'react';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';

interface ScreenshotGalleryProps {
  screenshots: string[];
}

export function ScreenshotGallery({ screenshots }: ScreenshotGalleryProps) {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  
  if (screenshots.length === 0) return null;
  
  return (
    <div className="mt-6">
      <h3 className="text-lg font-medium mb-2">Progress Captures ({screenshots.length})</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
        {screenshots.map((screenshot, index) => (
          <Dialog key={index}>
            <DialogTrigger asChild>
              <div 
                className="border rounded p-2 cursor-pointer hover:border-primary transition-colors"
                onClick={() => setSelectedImage(screenshot)}
              >
                <div className="aspect-video bg-muted rounded flex items-center justify-center">
                  <span className="text-sm text-muted-foreground">Step {index + 1}</span>
                </div>
                <div className="text-center text-xs mt-1 text-muted-foreground truncate">
                  {new Date(screenshot.split('_')[1]).toLocaleTimeString()}
                </div>
              </div>
            </DialogTrigger>
            <DialogContent className="sm:max-w-lg">
              <div className="aspect-video bg-muted rounded flex items-center justify-center">
                <span className="text-muted-foreground">
                  Screenshot Preview {index + 1}
                </span>
              </div>
              <div className="mt-2 text-center text-sm text-muted-foreground">
                Captured at {new Date(screenshot.split('_')[1]).toLocaleString()}
              </div>
            </DialogContent>
          </Dialog>
        ))}
      </div>
    </div>
  );
}
