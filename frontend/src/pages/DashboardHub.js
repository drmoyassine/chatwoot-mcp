import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import {
  Server, ChevronRight, LogOut, Key, Loader2, Plus,
  Play, Square, Trash2, GitBranch, Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AddServerModal } from "@/components/AddServerModal";

export default function DashboardHub() {
  const { axiosAuth, logout, user } = useAuth();
  const navigate = useNavigate();
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [actionLoading, setActionLoading] = useState({});

  const fetchApps = useCallback(() => {
    const api = axiosAuth();
    api.get("/api/apps")
      .then((r) => setApps(r.data.apps || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [axiosAuth]);

  useEffect(() => { fetchApps(); }, [fetchApps]);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const handleServerAction = async (e, serverName, action) => {
    e.stopPropagation();
    setActionLoading((p) => ({ ...p, [serverName]: action }));
    const api = axiosAuth();
    try {
      if (action === "start") {
        await api.post(`/api/servers/${serverName}/start`);
      } else if (action === "stop") {
        await api.post(`/api/servers/${serverName}/stop`);
      } else if (action === "delete") {
        if (!window.confirm(`Remove "${serverName}" and all its data?`)) return;
        await api.delete(`/api/servers/${serverName}`);
      }
      fetchApps();
    } catch (err) {
      console.error(`Action ${action} failed:`, err);
    } finally {
      setActionLoading((p) => ({ ...p, [serverName]: null }));
    }
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
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-xl font-bold text-[#0A0A0A] tracking-tight">Installed MCP Servers</h2>
            <p className="text-sm text-[#666] mt-1">Manage your Model Context Protocol integrations</p>
          </div>
          <Button
            onClick={() => setShowAddModal(true)}
            className="bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none font-mono text-xs"
            data-testid="add-server-button"
          >
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            Add MCP Server
          </Button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-[#002FA7]" />
          </div>
        ) : (
          <div className="grid gap-4">
            {apps.map((app) => (
              <div
                key={app.name}
                className="w-full bg-white border border-[#E5E5E5] hover:border-[#002FA7] hover:shadow-sm transition-all p-5 flex items-center gap-4 text-left group cursor-pointer"
                onClick={() => app.type === "builtin" ? navigate(`/dashboard/${app.name}`) : null}
                data-testid={`app-card-${app.name}`}
              >
                <div className={`w-12 h-12 flex items-center justify-center flex-shrink-0 border ${
                  app.type === "dynamic"
                    ? "bg-[#0A0A0A]/5 border-[#0A0A0A]/10"
                    : "bg-[#002FA7]/5 border-[#002FA7]/10"
                }`}>
                  {app.type === "dynamic"
                    ? <GitBranch className="w-5 h-5 text-[#0A0A0A]" />
                    : <Server className="w-6 h-6 text-[#002FA7]" />
                  }
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h3 className="font-bold text-[#0A0A0A] text-base">{app.display_name}</h3>
                    {app.type === "dynamic" && (
                      <Badge variant="outline" className="text-[9px] font-mono px-1.5 py-0 text-[#666] border-[#CCC]">
                        {app.runtime}
                      </Badge>
                    )}
                    {app.type === "dynamic" ? (
                      <Badge
                        variant="outline"
                        className={`text-[10px] font-mono uppercase px-1.5 py-0 ${
                          app.status === "connected"
                            ? "text-[#00E559] border-[#00E559]/30 bg-[#00E559]/5"
                            : app.configured
                              ? "text-[#FFCC00] border-[#FFCC00]/30 bg-[#FFCC00]/5"
                              : "text-[#999] border-[#999]/30 bg-[#999]/5"
                        }`}
                        data-testid={`server-status-${app.name}`}
                      >
                        {app.status === "connected" ? "Running" : app.configured ? "Stopped" : "Not configured"}
                      </Badge>
                    ) : (
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
                    )}
                  </div>
                  <p className="text-sm text-[#666] truncate">{app.description}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-[#999] font-mono">
                    {app.tools_count > 0 && <span>{app.tools_count} tools</span>}
                    <span className="flex items-center gap-1">
                      <Key className="w-3 h-3" />
                      {app.active_keys} key{app.active_keys !== 1 ? "s" : ""}
                    </span>
                    <span className="text-[#002FA7]">{app.mcp_endpoint}</span>
                  </div>
                </div>

                {/* Action buttons for dynamic servers */}
                {app.type === "dynamic" ? (
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {app.status === "connected" ? (
                      <Button
                        variant="ghost" size="icon"
                        className="w-8 h-8 text-[#999] hover:text-[#FF2A2A] hover:bg-[#FF2A2A]/5 rounded-none"
                        onClick={(e) => handleServerAction(e, app.name, "stop")}
                        disabled={actionLoading[app.name] === "stop"}
                        data-testid={`stop-server-${app.name}`}
                        title="Stop server"
                      >
                        {actionLoading[app.name] === "stop"
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Square className="w-3.5 h-3.5" />}
                      </Button>
                    ) : app.configured ? (
                      <Button
                        variant="ghost" size="icon"
                        className="w-8 h-8 text-[#999] hover:text-[#00E559] hover:bg-[#00E559]/5 rounded-none"
                        onClick={(e) => handleServerAction(e, app.name, "start")}
                        disabled={actionLoading[app.name] === "start"}
                        data-testid={`start-server-${app.name}`}
                        title="Start server"
                      >
                        {actionLoading[app.name] === "start"
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Play className="w-3.5 h-3.5" />}
                      </Button>
                    ) : null}
                    <Button
                      variant="ghost" size="icon"
                      className="w-8 h-8 text-[#999] hover:text-[#FF2A2A] hover:bg-[#FF2A2A]/5 rounded-none"
                      onClick={(e) => handleServerAction(e, app.name, "delete")}
                      disabled={!!actionLoading[app.name]}
                      data-testid={`delete-server-${app.name}`}
                      title="Remove server"
                    >
                      {actionLoading[app.name] === "delete"
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <Trash2 className="w-3.5 h-3.5" />}
                    </Button>
                  </div>
                ) : (
                  <ChevronRight className="w-5 h-5 text-[#CCC] group-hover:text-[#002FA7] transition-colors flex-shrink-0" />
                )}
              </div>
            ))}

            {/* Empty state */}
            {apps.length === 0 && (
              <div className="text-center py-16 text-[#999]">
                <Server className="w-10 h-10 mx-auto mb-3 text-[#DDD]" />
                <p className="font-mono text-sm">No MCP servers installed yet</p>
                <Button
                  onClick={() => setShowAddModal(true)}
                  className="mt-4 bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none font-mono text-xs"
                  data-testid="add-server-empty-button"
                >
                  <Plus className="w-3.5 h-3.5 mr-1.5" />
                  Add your first server
                </Button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Add Server Modal */}
      {showAddModal && (
        <AddServerModal
          onClose={() => setShowAddModal(false)}
          onAdded={() => { setShowAddModal(false); fetchApps(); }}
        />
      )}
    </div>
  );
}
