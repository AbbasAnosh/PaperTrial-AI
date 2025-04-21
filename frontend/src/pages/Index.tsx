import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { DocumentUpload } from "@/components/DocumentUpload";
import { ProcessingStatus } from "@/components/ProcessingStatus";
import { SubmissionHistory } from "@/components/SubmissionHistory";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowRight, LogOut, Upload, History, UserCircle } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { useAuth } from "@/hooks/useAuth";
import { Link } from "react-router-dom";
import { ThemeToggle } from "@/components/theme-toggle";

const Index = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user, signOut } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [currentStep, setCurrentStep] = useState(-1);
  const [processingStatus, setProcessingStatus] = useState<
    "wait" | "process" | "finish" | "error"
  >("wait");

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate("/auth");
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error signing out",
        description:
          error instanceof Error ? error.message : "An error occurred",
      });
    }
  };

  const handleFileUpload = async (file: File) => {
    try {
      setUploading(true);
      setCurrentStep(0);
      setProcessingStatus("process");

      const userId = user?.id;
      if (!userId) throw new Error("User not authenticated");

      const filePath = `${userId}/${file.name}`;
      const { error: uploadError } = await supabase.storage
        .from("documents")
        .upload(filePath, file);

      if (uploadError) throw uploadError;

      setCurrentStep(1);
      const { error: dbError } = await supabase.from("documents").insert({
        file_name: file.name,
        file_path: filePath,
        file_type: file.type,
        original_name: file.name,
        size: file.size,
        user_id: userId,
      });

      if (dbError) throw dbError;

      setCurrentStep(2);
      // Create a submission record
      const { error: submissionError } = await supabase
        .from("submissions")
        .insert({
          document_id: null, // Will be updated once we process the document
          user_id: userId,
          status: "pending",
        });

      if (submissionError) throw submissionError;

      setCurrentStep(3);
      setProcessingStatus("finish");
      toast({
        title: "Success!",
        description: "Document uploaded and queued for processing",
      });
    } catch (error) {
      setProcessingStatus("error");
      toast({
        variant: "destructive",
        title: "Error uploading document",
        description:
          error instanceof Error ? error.message : "An error occurred",
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <main className="flex-1 p-6">
          <div className="flex justify-between items-center mb-6">
            <SidebarTrigger />
            <div className="flex items-center space-x-4">
              <ThemeToggle />
              <Link to="/profile" className="flex items-center">
                <UserCircle className="h-5 w-5 mr-2" />
                <span>{user?.email}</span>
              </Link>
              <Button variant="ghost" onClick={handleSignOut}>
                <LogOut className="h-4 w-4 mr-2" />
                Sign out
              </Button>
            </div>
          </div>

          <div className="max-w-4xl mx-auto space-y-8">
            <div className="text-center">
              <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl mb-4">
                PaperTrail AI
              </h1>
              <p className="text-lg text-muted-foreground mb-8">
                Automate your document processing with artificial intelligence
              </p>
              <div className="flex justify-center gap-4">
                <Button size="lg" asChild>
                  <Link to="/profile">
                    Complete Your Profile
                    <UserCircle className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg">
                  Learn More
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>

            <Tabs defaultValue="upload" className="mt-12">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="upload" className="flex items-center">
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Document
                </TabsTrigger>
                <TabsTrigger value="history" className="flex items-center">
                  <History className="mr-2 h-4 w-4" />
                  Submission History
                </TabsTrigger>
              </TabsList>

              <TabsContent value="upload" className="mt-6">
                <DocumentUpload
                  onFileSelect={handleFileUpload}
                  disabled={uploading}
                />
                <ProcessingStatus
                  currentStep={currentStep}
                  status={processingStatus}
                />
              </TabsContent>

              <TabsContent value="history" className="mt-6">
                <SubmissionHistory />
              </TabsContent>
            </Tabs>
          </div>
        </main>
      </div>
    </SidebarProvider>
  );
};

export default Index;
