import { Link, useLocation } from "react-router-dom";
import { Sidebar } from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { LogOut, Home, User, FileText, FileCheck } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/components/ui/use-toast";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { signOut, user } = useAuth();
  const [userName, setUserName] = useState<string>("");

  useEffect(() => {
    const fetchUserName = async () => {
      if (!user) return;

      try {
        const { data, error } = await supabase
          .from("profiles")
          .select("first_name, last_name")
          .eq("id", user.id)
          .single();

        if (error) throw error;
        if (data) {
          setUserName(
            `${data.first_name} ${data.last_name}`.trim() ||
              user.email ||
              "User"
          );
        }
      } catch (error) {
        console.error("Error fetching user name:", error);
        setUserName(user.email || "User");
      }
    };

    fetchUserName();
  }, [user]);

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

  return (
    <Sidebar className="border-r bg-background h-screen">
      <div className="flex flex-col h-full">
        <div className="flex items-center h-14 px-4 border-b">
          <Link to="/" className="flex items-center space-x-2">
            <FileCheck className="h-6 w-6" />
            <span className="font-bold">PaperTrail AI</span>
          </Link>
          {/* We're removing the SidebarClose component since it doesn't exist */}
        </div>
        <div className="flex-1 py-2">
          <div className="px-3 py-2">
            <h3 className="text-xs font-medium text-muted-foreground tracking-wider">
              MAIN NAVIGATION
            </h3>
            <div className="mt-2 space-y-1">
              <Button
                variant={location.pathname === "/" ? "secondary" : "ghost"}
                asChild
                className="w-full justify-start"
              >
                <Link to="/">
                  <Home className="mr-2 h-4 w-4" />
                  Dashboard
                </Link>
              </Button>
              <Button
                variant={location.pathname === "/forms" ? "secondary" : "ghost"}
                asChild
                className="w-full justify-start"
              >
                <Link to="/forms">
                  <FileText className="mr-2 h-4 w-4" />
                  Forms
                </Link>
              </Button>
              <Button
                variant={
                  location.pathname === "/profile" ? "secondary" : "ghost"
                }
                asChild
                className="w-full justify-start"
              >
                <Link to="/profile">
                  <User className="mr-2 h-4 w-4" />
                  Profile
                </Link>
              </Button>
            </div>
          </div>
        </div>
        <div className="p-4 border-t">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <User className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">{userName}</span>
            </div>
          </div>
          <Button variant="outline" className="w-full" onClick={handleSignOut}>
            <LogOut className="mr-2 h-4 w-4" />
            Sign Out
          </Button>
        </div>
      </div>
    </Sidebar>
  );
}
