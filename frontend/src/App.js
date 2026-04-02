import "@/App.css";
import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Login from "@/pages/Login";
import DashboardHub from "@/pages/DashboardHub";
import ChatwootDashboard from "@/pages/ChatwootDashboard";
import ServerDashboard from "@/pages/ServerDashboard";

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardHub />} />
          <Route path="/dashboard/chatwoot" element={<ChatwootDashboard />} />
          <Route path="/dashboard/:serverName" element={<ServerDashboard />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  );
}

export default App;
