import { useEffect, useState } from "react";
import { FormTemplate } from "@/types/form";
import { FormTemplateService } from "@/services/formTemplateService";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";

export const FormCatalog = () => {
  const [forms, setForms] = useState<FormTemplate[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const loadData = async () => {
      try {
        const [formData, categoryData] = await Promise.all([
          FormTemplateService.getFormCatalog(),
          FormTemplateService.getFormCategories(),
        ]);
        setForms(formData);
        setCategories(categoryData);
      } catch (error) {
        console.error("Error loading form catalog:", error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      const data = await FormTemplateService.getFormCatalog();
      setForms(data);
      return;
    }

    const results = await FormTemplateService.searchForms(searchQuery);
    setForms(results);
  };

  const handleCategorySelect = async (category: string) => {
    setSelectedCategory(category);
    if (category === "") {
      const data = await FormTemplateService.getFormCatalog();
      setForms(data);
    } else {
      const data = await FormTemplateService.getFormsByCategory(category);
      setForms(data);
    }
  };

  if (loading) {
    return <div>Loading form catalog...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Input
            placeholder="Search forms..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-500" />
        </div>
        <Button onClick={handleSearch}>Search</Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          variant={selectedCategory === "" ? "default" : "outline"}
          onClick={() => handleCategorySelect("")}
        >
          All Forms
        </Button>
        {categories.map((category) => (
          <Button
            key={category}
            variant={selectedCategory === category ? "default" : "outline"}
            onClick={() => handleCategorySelect(category)}
          >
            {category}
          </Button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {forms.map((form) => (
          <Card
            key={form.id}
            className="cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => navigate(`/forms/${form.id}`)}
          >
            <CardHeader>
              <CardTitle>{form.name}</CardTitle>
              <CardDescription>{form.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Badge variant="secondary">{form.category}</Badge>
                <p className="text-sm text-gray-500">
                  Estimated time: {form.guidance?.estimatedTime || "Varies"}
                </p>
                <div className="flex flex-wrap gap-2">
                  {form.guidance?.requiredDocuments?.map((doc) => (
                    <Badge key={doc} variant="outline">
                      {doc}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};
