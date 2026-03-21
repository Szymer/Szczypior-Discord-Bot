import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/context/AuthContext";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import RankingPage from "@/pages/RankingPage";
import StatsPage from "@/pages/StatsPage";
import HistoryPage from "@/pages/HistoryPage";
import RulesPage from "@/pages/RulesPage";
import HomePage from "@/pages/HomePage";
import ChallengePage from "@/pages/ChallengePage";
import EventPage from "@/pages/EventPage";
import AdminPage from "@/pages/AdminPage";
import ProtectedRoute from "@/components/ProtectedRoute";
import NotFound from "@/pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<LoginPage />} />
            <Route path="/home" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/ranking" element={<ProtectedRoute><RankingPage /></ProtectedRoute>} />
            <Route path="/stats" element={<ProtectedRoute><StatsPage /></ProtectedRoute>} />
            <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
            <Route path="/rules" element={<ProtectedRoute><RulesPage /></ProtectedRoute>} />
            <Route path="/challenges" element={<ProtectedRoute><ChallengePage /></ProtectedRoute>} />
            <Route path="/challenge/:id" element={<ProtectedRoute><ChallengePage /></ProtectedRoute>} />
            <Route path="/event/:id" element={<ProtectedRoute><EventPage /></ProtectedRoute>} />
            <Route path="/admin" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
