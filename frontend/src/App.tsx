import React, { useState } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./contexts/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import Login from "./components/Login";
import Register from "./components/Register";
import { FormUpload } from "./components/FormUpload";
import { FormPreview } from "./components/FormPreview";
import { QuestionAnswer } from "./components/QuestionAnswer";
import { toast } from "react-hot-toast";

const App: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<"upload" | "preview" | "qa">(
    "upload"
  );
  const [formId, setFormId] = useState<string | null>(null);
  const [formFields, setFormFields] = useState<any[]>([]);

  const handleUploadComplete = (formData: any) => {
    setFormId(formData.id);
    setFormFields(formData.fields);
    setCurrentStep("preview");
  };

  const handleUploadError = (error: string) => {
    toast.error(error);
  };

  const handleStartQA = () => {
    setCurrentStep("qa");
  };

  const handleEditFields = () => {
    setCurrentStep("preview");
  };

  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-background">
          <Toaster position="top-right" />
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  {currentStep === "upload" && (
                    <FormUpload
                      onUploadComplete={handleUploadComplete}
                      onError={handleUploadError}
                    />
                  )}
                  {currentStep === "preview" && (
                    <FormPreview
                      formId={formId!}
                      fields={formFields}
                      onStartQA={handleStartQA}
                      onEditFields={handleEditFields}
                    />
                  )}
                  {currentStep === "qa" && (
                    <QuestionAnswer
                      formId={formId!}
                      fields={formFields}
                      onComplete={() => setCurrentStep("upload")}
                      onCancel={() => setCurrentStep("preview")}
                    />
                  )}
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
};

export default App;
