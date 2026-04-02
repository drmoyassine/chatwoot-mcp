import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate, useParams } from "react-router-dom";
import { Server, Play, Loader as Loader2, CircleAlert as AlertCircle, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sidebar } from "@/components/Sidebar";
import { ApiKeyManager } from "@/components/ApiKeyManager";
import { ToolExplorer } from "@/components/ToolExplorer";
import { TestTerminal } from "@/components/TestTerminal";
import { CreateToolModal } from "@/components/CreateToolModal";
import { ParamEditModal } from "@/components/ParamEditModal";
import { FilterTab } from "@/components/FilterTab";
import { WebhookEvents } from "@/components/WebhookEvents";

export default function ServerDashboard() {
  const { serverName } = useParams();
  const { axiosAuth, logout } = useAuth();
  const navigate = useNavigate();

  const [serverInfo, setServerInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tools, setTools] = useState([]);
  const [selectedTool, setSelectedTool] = useState(null);
  const [activeTab, setActiveTab] = useState("tools");
  const [actionLoading, setActionLoading] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateTool, setShowCreateTool] = useState(false);
  const [outputFormat, setOutputFormat] = useState("json");
  const [editingParam, setEditingParam] = useState(null);
  const [addingParam, setAddingParam] = useState(null);
  const [credentials, setCredentials] = useState({});
  const [savingCreds, setSavingCreds] = useState(false);

  const api = useCallback(() => axiosAuth(), [axiosAuth]);

  const fetchServer = useCallback(async () => {
    try {
      const resp = await api().get(`/api/servers/${serverName}`);
      setServerInfo(resp.data);
    } catch (e) {
      console.error("Failed to fetch server", e);
    } finally {
      setLoading(false);
    }
  }, [api, serverName]);

  const fetchCredentials = useCallback(async () => {
    try {
      const resp = await api().get(`/api/servers/${serverName}/credentials`);
      setCredentials(resp.data.credentials || {});
    } catch (e) {
      console.error("Failed to fetch credentials", e);
    }
  }, [api, serverName]);

  const fetchTools = useCallback(async () => {
    try {
      const resp = await api().get(`/api/servers/${serverName}/tools`);
      const rawTools = resp.data.tools || [];
      setTools(rawTools.map((t) => ({
        ...t,
        category: t.category || "general",
        parameters: t.parameters || [],
        enabled: t.enabled !== false,
        source: t.source || "builtin",
      })));
    } catch (e) {
      setTools([]);
    }
  }, [api, serverName]);

  const fetchOutputFormat = useCallback(async () => {
    try {
      const resp = await api().get(`/api/servers/${serverName}/output-format`);
      setOutputFormat(resp.data.output_format || "json");
    } catch (e) {
      console.error("Failed to fetch output format", e);
    }
  }, [api, serverName]);

  useEffect(() => {
    fetchServer();
    fetchCredentials();
    fetchTools();
    fetchOutputFormat();
  }, [fetchServer, fetchCredentials, fetchTools, fetchOutputFormat]);

  const handleStartStop = async (action) => {
    setActionLoading(action);
    try {
      await api().post(`/api/servers/${serverName}/${action}`);
      await fetchServer();
      if (action === "start") await fetchTools();
      else setTools([]);
    } catch (e) {
      console.error(`${action} failed`, e);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRestart = async () => {
    setActionLoading("restart");
    try {
      await api().post(`/api/servers/${serverName}/stop`);
      await api().post(`/api/servers/${serverName}/start`);
      await fetchServer();
      await fetchTools();
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSaveCredentials = async (credInputs, schema) => {
    setSavingCreds(true);
    try {
      await api().post(`/api/servers/${serverName}/credentials`, {
        credentials: credInputs,
        credentials_schema: schema || serverInfo.credentials_schema || [],
      });
      await fetchCredentials();
      await fetchServer();
    } catch (e) {
      console.error("Failed to save credentials", e);
    } finally {
      setSavingCreds(false);
    }
  };

  const handleOutputFormatChange = async (fmt) => {
    try {
      await api().post(`/api/servers/${serverName}/output-format`, { output_format: fmt });
      setOutputFormat(fmt);
    } catch (e) {
      console.error("Failed to save output format", e);
    }
  };

  const executeTool = async (toolName, parameters) => {
    const resp = await api().post(`/api/servers/${serverName}/tools/execute`, {
      tool_name: toolName,
      parameters,
    });
    return resp.data;
  };

  const handleSaveParam = async (paramData) => {
    const toolName = editingParam?.tool?.name || addingParam?.name;
    if (!toolName) return;
    try {
      await api().put(
        `/api/servers/${serverName}/tools/${toolName}/params/${paramData.name}`,
        paramData,
      );
      await fetchTools();
      if (selectedTool?.name === toolName) {
        const updatedTools = (await api().get(`/api/servers/${serverName}/tools`)).data.tools;
        const updated = updatedTools.find((t) => t.name === toolName);
        if (updated) setSelectedTool(updated);
      }
    } catch (e) {
      console.error("Failed to save param", e);
    }
    setEditingParam(null);
    setAddingParam(null);
  };

  const handleToggleTool = async (toolName, enabled) => {
    try {
      await api().put(`/api/tools/${serverName}/${toolName}`, { enabled });
      await fetchTools();
      if (selectedTool?.name === toolName) {
        setSelectedTool((t) => (t ? { ...t, enabled } : t));
      }
    } catch (e) {
      console.error("Failed to toggle tool", e);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#F5F5F5]">
        <Loader2 className="w-6 h-6 animate-spin text-[#002FA7]" />
      </div>
    );
  }

  if (!serverInfo) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-[#F5F5F5] gap-4">
        <AlertCircle className="w-8 h-8 text-[#FF2A2A]" />
        <p className="font-mono text-sm text-[#666]">Server "{serverName}" not found</p>
        <Button onClick={() => navigate("/dashboard")} variant="outline" className="rounded-none font-mono text-xs">
          Back to Hub
        </Button>
      </div>
    );
  }

  const isRunning = serverInfo.status === "connected";
  const connectionStatus = isRunning ? "connected" : "disconnected";
  const features = serverInfo.features || [];
  const categories = ["all", ...new Set(tools.map((t) => t.category))].sort();
  const filteredTools = tools.filter((t) => {
    const matchesCategory = selectedCategory === "all" || t.category === selectedCategory;
    const matchesSearch = !searchQuery || t.name.toLowerCase().includes(searchQuery.toLowerCase()) || (t.description || "").toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const TABS = [
    { id: "tools", label: `Tools${tools.length ? ` (${tools.length})` : ""}` },
    ...(features.includes("filters") ? [{ id: "filters", label: "Filters" }] : []),
    ...(features.includes("webhooks") ? [{ id: "webhooks", label: "Webhooks" }] : []),
    { id: "apikeys", label: "API Keys" },
  ];

  return (
    <div className="h-screen w-full flex flex-col md:flex-row overflow-hidden" data-testid="server-dashboard">
      <Sidebar
        serverInfo={serverInfo}
        serverName={serverName}
        isRunning={isRunning}
        toolsCount={tools.length}
        credentials={credentials}
        onSaveCredentials={handleSaveCredentials}
        savingCreds={savingCreds}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        tabs={TABS}
        outputFormat={outputFormat}
        onOutputFormatChange={handleOutputFormatChange}
        onBack={() => navigate("/dashboard")}
        onLogout={handleLogout}
        onStartStop={handleStartStop}
        onRestart={handleRestart}
        actionLoading={actionLoading}
      />

      <div className="flex-1 flex flex-col overflow-hidden border-l border-[#E5E5E5]">
        {activeTab === "tools" && (
          <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
            {!isRunning && tools.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 gap-3 bg-white">
                <Server className="w-10 h-10 text-[#DDD]" />
                <p className="font-mono text-sm text-[#999]">Server is not running</p>
                <p className="text-xs text-[#999]">Start the server to discover available tools, or create a custom tool</p>
                <div className="flex gap-2 mt-2">
                  <Button
                    size="sm"
                    className="bg-[#00A040] hover:bg-[#008030] text-white rounded-none text-xs font-mono"
                    onClick={() => handleStartStop("start")}
                    disabled={!!actionLoading || !serverInfo.has_credentials}
                    data-testid="start-server-inline"
                  >
                    <Play className="w-3 h-3 mr-1.5" />
                    Start Server
                  </Button>
                  <Button
                    size="sm"
                    className="bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none text-xs font-mono"
                    onClick={() => setShowCreateTool(true)}
                    data-testid="create-tool-inline"
                  >
                    <Plus className="w-3 h-3 mr-1.5" />
                    New Tool
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <ToolExplorer
                  tools={filteredTools}
                  categories={categories}
                  selectedCategory={selectedCategory}
                  onCategoryChange={setSelectedCategory}
                  searchQuery={searchQuery}
                  onSearchChange={setSearchQuery}
                  selectedTool={selectedTool}
                  onSelectTool={setSelectedTool}
                  onEditParam={(tool, param) => setEditingParam({ tool, param })}
                  onAddParam={(tool) => setAddingParam(tool)}
                  onToggleTool={handleToggleTool}
                  onCreateTool={() => setShowCreateTool(true)}
                />
                <TestTerminal
                  selectedTool={selectedTool}
                  onExecute={executeTool}
                  connectionStatus={connectionStatus}
                  onEditParam={(tool, param) => setEditingParam({ tool, param })}
                  onAddParam={(tool) => setAddingParam(tool)}
                  appName={serverName}
                />
              </>
            )}
          </div>
        )}

        {activeTab === "filters" && (
          <FilterTab executeTool={executeTool} connectionStatus={connectionStatus} />
        )}

        {activeTab === "webhooks" && (
          <div className="flex-1 flex flex-col overflow-hidden bg-white">
            <WebhookEvents serverName={serverName} />
          </div>
        )}

        {activeTab === "apikeys" && (
          <div className="flex-1 flex flex-col overflow-hidden bg-white">
            <ApiKeyManager appName={serverName} />
          </div>
        )}
      </div>

      {editingParam && (
        <ParamEditModal
          param={editingParam.param}
          toolName={editingParam.tool.name}
          onSave={handleSaveParam}
          onClose={() => setEditingParam(null)}
        />
      )}
      {addingParam && (
        <ParamEditModal
          param={null}
          toolName={addingParam.name}
          onSave={handleSaveParam}
          onClose={() => setAddingParam(null)}
        />
      )}
      {showCreateTool && (
        <CreateToolModal
          categories={categories}
          onClose={() => setShowCreateTool(false)}
          onCreated={fetchTools}
          appName={serverName}
        />
      )}
    </div>
  );
}
