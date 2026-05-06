import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate, useLocation } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/lib/theme-provider";
import { AuthProvider, useAuth } from "@/lib/AuthProvider";
import { WorkspaceProvider } from "@/lib/WorkspaceProvider";
import { AppShell } from "@/components/AppShell";

import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import NewResearch from "./pages/NewResearch";
import Runs from "./pages/Runs";
import RunDetail from "./pages/RunDetail";
import Reports from "./pages/Reports";
import ReportViewer from "./pages/ReportViewer";
import RAGChats from "./pages/RAGChat";
import SourcesPage from "./pages/SourcesPage";
import Visualizations from "./pages/Visualizations";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="h-6 w-6 border-2 border-gold border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider>
      <AuthProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route
                element={
                  <ProtectedRoute>
                    <WorkspaceProvider>
                      <AppShell />
                    </WorkspaceProvider>
                  </ProtectedRoute>
                }
              >
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/new" element={<NewResearch />} />
                <Route path="/runs" element={<Runs />} />
                <Route path="/runs/:id" element={<RunDetail />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/report" element={<ReportViewer />} />
                <Route path="/chats" element={<RAGChats />} />
                <Route path="/chats/:id" element={<RAGChats />} />
                <Route path="/sources" element={<SourcesPage />} />
                <Route path="/visualizations" element={<Visualizations />} />
                <Route path="/settings" element={<Settings />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </TooltipProvider>
      </AuthProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
