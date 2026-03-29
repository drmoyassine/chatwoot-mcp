import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { Server, Wifi, WifiOff, ChevronRight, LogOut, Key, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function DashboardHub() {
  const { axiosAuth, logout, user } = useAuth();
  const navigate = useNavigate();
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const api = axiosAuth();
    api.get("/api/apps")
      .then((r) => setApps(r.data.apps || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [axiosAuth]);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-[#F5F5F5]" data-testid="dashboard-hub">
      {/* Top Bar */}
      <header className="bg-[#0A0A0A] border-b border-[#222] px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#002FA7] flex items-center justify-center">
            <Server className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight">MCP Hub</h1>
            <p className="text-[10px] text-[#666] font-mono uppercase">Control Room</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-[#888] font-mono" data-testid="user-email">{user?.email}</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="text-[#888] hover:text-white hover:bg-[#222] rounded-none text-xs font-mono"
            data-testid="logout-button"
          >
            <LogOut className="w-3.5 h-3.5 mr-1.5" />
            Logout
          </Button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-6 py-10">
        <div className="mb-8">
          <h2 className="text-xl font-bold text-[#0A0A0A] tracking-tight">Installed MCP Servers</h2>
          <p className="text-sm text-[#666] mt-1">Manage your Model Context Protocol integrations</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-[#002FA7]" />
          </div>
        ) : (
          <div className="grid gap-4">
            {apps.map((app) => (
              <button
                key={app.name}
                onClick={() => navigate(`/dashboard/${app.name}`)}
                className="w-full bg-white border border-[#E5E5E5] hover:border-[#002FA7] hover:shadow-sm transition-all p-5 flex items-center gap-4 text-left group"
                data-testid={`app-card-${app.name}`}
              >
                <div className="w-12 h-12 bg-[#002FA7]/5 border border-[#002FA7]/10 flex items-center justify-center flex-shrink-0">
                  <Server className="w-6 h-6 text-[#002FA7]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-bold text-[#0A0A0A] text-base">{app.display_name}</h3>
                    <Badge
                      variant="outline"
                      className={`text-[10px] font-mono uppercase px-1.5 py-0 ${
                        app.configured
                          ? "text-[#00E559] border-[#00E559]/30 bg-[#00E559]/5"
                          : "text-[#999] border-[#999]/30 bg-[#999]/5"
                      }`}
                    >
                      {app.configured ? "Connected" : "Not configured"}
                    </Badge>
                  </div>
                  <p className="text-sm text-[#666] truncate">{app.description}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-[#999] font-mono">
                    <span>{app.tools_count} tools</span>
                    <span className="flex items-center gap-1">
                      <Key className="w-3 h-3" />
                      {app.active_keys} active key{app.active_keys !== 1 ? "s" : ""}
                    </span>
                    <span className="text-[#002FA7]">{app.mcp_endpoint}</span>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-[#CCC] group-hover:text-[#002FA7] transition-colors flex-shrink-0" />
              </button>
            ))}

            {apps.length === 0 && (
              <div className="text-center py-16 text-[#999]">
                <Server className="w-10 h-10 mx-auto mb-3 text-[#DDD]" />
                <p className="font-mono text-sm">No MCP servers installed yet</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
