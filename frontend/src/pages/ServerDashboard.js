import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate, useParams } from "react-router-dom";
import {
  Server, ArrowLeft, LogOut, Play, Square, Loader2, RefreshCw,
  Settings, ChevronDown, ChevronRight, Eye, EyeOff, Save, Radio,
  Key, GitBranch, AlertCircle, Wifi, WifiOff, Zap, Plus, Trash2,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ApiKeyManager } from "@/components/ApiKeyManager";

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

  // Credentials
  const [credentials, setCredentials] = useState({});
  const [credInputs, setCredInputs] = useState({});
  const [editingCreds, setEditingCreds] = useState(false);
  const [savingCreds, setSavingCreds] = useState(false);
  const [showValues, setShowValues] = useState({});
  const [newEnvKey, setNewEnvKey] = useState("");

  // Tool execution
  const [execResult, setExecResult] = useState(null);
  const [execError, setExecError] = useState(null);
  const [execLoading, setExecLoading] = useState(false);
  const [paramValues, setParamValues] = useState({});
  const [elapsed, setElapsed] = useState(null);

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
      setTools(resp.data.tools || []);
    } catch (e) {
      setTools([]);
    }
  }, [api, serverName]);

  useEffect(() => {
    fetchServer();
    fetchCredentials();
    fetchTools();
  }, [fetchServer, fetchCredentials, fetchTools]);

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

  const handleSaveCredentials = async () => {
    setSavingCreds(true);
    try {
      await api().post(`/api/servers/${serverName}/credentials`, {
        credentials: credInputs,
        credentials_schema: serverInfo.credentials_schema || [],
      });
      setEditingCreds(false);
      setCredInputs({});
      setNewEnvKey("");
      await fetchCredentials();
      await fetchServer();
    } catch (e) {
      console.error("Failed to save credentials", e);
    } finally {
      setSavingCreds(false);
    }
  };

  const executeTool = async (toolName, parameters) => {
    setExecLoading(true);
    setExecError(null);
    setExecResult(null);
    const start = performance.now();
    try {
      const resp = await api().post(`/api/servers/${serverName}/tools/execute`, {
        tool_name: toolName,
        parameters,
      });
      setExecResult(resp.data.result);
      setElapsed(Math.round(performance.now() - start));
    } catch (e) {
      setExecError(e.response?.data?.detail || e.message || "Execution failed");
      setElapsed(Math.round(performance.now() - start));
    } finally {
      setExecLoading(false);
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
  const TABS = [
    { id: "tools", label: `Tools${tools.length ? ` (${tools.length})` : ""}` },
    { id: "apikeys", label: "API Keys" },
  ];

  return (
    <div className="h-screen w-full flex flex-col md:flex-row overflow-hidden" data-testid="server-dashboard">
      {/* Sidebar */}
      <aside className="w-full md:w-80 flex-shrink-0 bg-[#F5F5F5] border-r border-[#E5E5E5] flex flex-col overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-[#E5E5E5]">
          <button
            onClick={() => navigate("/dashboard")}
            className="flex items-center gap-1.5 text-xs text-[#666] hover:text-[#002FA7] font-mono mb-3 transition-colors"
            data-testid="sidebar-back-button"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            All Servers
          </button>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-8 h-8 bg-[#0A0A0A] flex items-center justify-center">
              <GitBranch className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-lg font-bold tracking-tight text-[#0A0A0A] truncate" data-testid="server-title">
                {serverInfo.display_name || serverName}
              </h1>
              <p className="text-xs text-[#666] font-mono uppercase">{serverInfo.runtime} MCP SERVER</p>
            </div>
            <button onClick={handleLogout} className="text-[#999] hover:text-[#FF2A2A] transition-colors" title="Logout">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center gap-2 mt-3">
            {isRunning ? <Wifi className="w-3.5 h-3.5 text-[#00E559]" /> : <WifiOff className="w-3.5 h-3.5 text-[#999]" />}
            <Badge
              variant="outline"
              className={`text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 border ${
                isRunning
                  ? "bg-[#00E559]/10 text-[#00E559] border-[#00E559]/20"
                  : "bg-[#999]/10 text-[#666] border-[#999]/20"
              }`}
              data-testid="server-status-badge"
            >
              {isRunning ? "RUNNING" : "STOPPED"}
            </Badge>
            {isRunning && tools.length > 0 && (
              <span className="text-xs text-[#666] font-mono">{tools.length} tools</span>
            )}
          </div>

          {/* Start / Stop */}
          <div className="flex gap-2 mt-4">
            {isRunning ? (
              <Button
                size="sm"
                className="flex-1 bg-[#FF2A2A] hover:bg-[#CC0000] text-white rounded-none text-xs font-mono"
                onClick={() => handleStartStop("stop")}
                disabled={!!actionLoading}
                data-testid="stop-server-button"
              >
                {actionLoading === "stop" ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <Square className="w-3 h-3 mr-1.5" />}
                Stop
              </Button>
            ) : (
              <Button
                size="sm"
                className="flex-1 bg-[#00A040] hover:bg-[#008030] text-white rounded-none text-xs font-mono"
                onClick={() => handleStartStop("start")}
                disabled={!!actionLoading || !serverInfo.has_credentials}
                data-testid="start-server-button"
                title={!serverInfo.has_credentials ? "Configure credentials first" : ""}
              >
                {actionLoading === "start" ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <Play className="w-3 h-3 mr-1.5" />}
                Start
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              className="rounded-none text-xs font-mono"
              onClick={async () => {
                setActionLoading("restart");
                try {
                  await api().post(`/api/servers/${serverName}/stop`);
                  await api().post(`/api/servers/${serverName}/start`);
                  await fetchServer();
                  await fetchTools();
                } catch (e) { console.error(e); }
                finally { setActionLoading(null); }
              }}
              disabled={!!actionLoading || !isRunning}
              data-testid="restart-server-button"
            >
              {actionLoading === "restart" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            </Button>
          </div>
        </div>

        {/* Credentials */}
        <Collapsible defaultOpen={!serverInfo.has_credentials}>
          <CollapsibleTrigger className="w-full flex items-center justify-between px-6 py-3 border-b border-[#E5E5E5] hover:bg-[#EBEBEB] transition-colors duration-150">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-[#666]">
              <Settings className="w-3.5 h-3.5 inline mr-2" />
              Credentials
            </span>
            <ChevronDown className="w-4 h-4 text-[#666]" />
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="p-4 space-y-3 border-b border-[#E5E5E5]">
              {!editingCreds ? (
                <>
                  {serverInfo.credentials_schema?.length > 0 ? (
                    serverInfo.credentials_schema.map((cs) => (
                      <div key={cs.key}>
                        <label className="text-xs font-medium text-[#666] mb-1 block uppercase">{cs.label || cs.key}</label>
                        <div className="font-mono text-sm text-[#0A0A0A] bg-white border border-[#E5E5E5] px-3 py-2 flex items-center justify-between">
                          <span className="truncate" data-testid={`cred-display-${cs.key}`}>
                            {credentials[cs.key] || (serverInfo.has_credentials ? "***" : "Not set")}
                          </span>
                          {credentials[cs.key] && (
                            <button onClick={() => setShowValues((v) => ({ ...v, [cs.key]: !v[cs.key] }))} className="text-[#666] hover:text-[#0A0A0A] ml-2">
                              {showValues[cs.key] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                            </button>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div>
                      <label className="text-xs font-medium text-[#666] mb-1 block">STATUS</label>
                      <div className="font-mono text-sm text-[#0A0A0A] bg-white border border-[#E5E5E5] px-3 py-2">
                        {serverInfo.has_credentials ? "Configured" : "No credentials saved"}
                      </div>
                    </div>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full rounded-none text-xs font-mono"
                    onClick={() => setEditingCreds(true)}
                    data-testid="edit-credentials-button"
                  >
                    <Settings className="w-3 h-3 mr-1.5" />
                    {serverInfo.has_credentials ? "Update Credentials" : "Configure Credentials"}
                  </Button>
                </>
              ) : (
                <>
                  {/* Existing schema entries */}
                  {(serverInfo.credentials_schema?.length > 0
                    ? serverInfo.credentials_schema
                    : [{ key: "API_KEY", label: "API Key", required: false }]
                  ).map((cs) => (
                    <div key={cs.key}>
                      <label className="text-xs font-medium text-[#0A0A0A] mb-1 block uppercase">
                        {cs.label || cs.key}
                        {cs.required && <span className="text-[#FF2A2A] ml-1">*</span>}
                      </label>
                      <Input
                        type="password"
                        value={credInputs[cs.key] || ""}
                        onChange={(e) => setCredInputs((c) => ({ ...c, [cs.key]: e.target.value }))}
                        placeholder={`Enter ${cs.label || cs.key}...`}
                        className="rounded-none border-[#E5E5E5] font-mono text-sm"
                        data-testid={`cred-input-${cs.key}`}
                      />
                      {cs.hint && <p className="text-[10px] text-[#999] mt-1">{cs.hint}</p>}
                    </div>
                  ))}

                  {/* Add new env var */}
                  <div className="pt-2 border-t border-dashed border-[#E5E5E5]">
                    <label className="text-[10px] font-medium text-[#999] mb-1.5 block uppercase tracking-wider">
                      Add custom environment variable
                    </label>
                    <div className="flex gap-2">
                      <Input
                        value={newEnvKey}
                        onChange={(e) => setNewEnvKey(e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, ""))}
                        placeholder="ENV_VAR_NAME"
                        className="flex-1 rounded-none border-[#E5E5E5] font-mono text-xs h-7"
                        data-testid="new-env-key-input"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        className="rounded-none text-xs h-7 px-2"
                        disabled={!newEnvKey.trim()}
                        onClick={() => {
                          if (!newEnvKey.trim()) return;
                          const key = newEnvKey.trim();
                          // Add to schema
                          const schema = [...(serverInfo.credentials_schema || [])];
                          if (!schema.find((s) => s.key === key)) {
                            schema.push({ key, label: key, required: false });
                            setServerInfo((s) => ({ ...s, credentials_schema: schema }));
                          }
                          setNewEnvKey("");
                        }}
                        data-testid="add-new-env-button"
                      >
                        <Plus className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="flex-1 rounded-none text-xs" onClick={() => { setEditingCreds(false); setCredInputs({}); setNewEnvKey(""); }}>
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      className="flex-1 bg-[#002FA7] text-white hover:bg-[#001B66] rounded-none text-xs"
                      onClick={handleSaveCredentials}
                      disabled={savingCreds}
                      data-testid="save-credentials-button"
                    >
                      {savingCreds ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Save className="w-3 h-3 mr-1.5" />}
                      Save
                    </Button>
                  </div>
                </>
              )}
            </div>
          </CollapsibleContent>
        </Collapsible>

        {/* Server Info */}
        <Collapsible>
          <CollapsibleTrigger className="w-full flex items-center justify-between px-6 py-3 border-b border-[#E5E5E5] hover:bg-[#EBEBEB] transition-colors duration-150">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-[#666]">
              <Radio className="w-3.5 h-3.5 inline mr-2" />
              Server Info
            </span>
            <ChevronRight className="w-4 h-4 text-[#666]" />
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="p-4 space-y-3 border-b border-[#E5E5E5]">
              <div>
                <label className="text-xs font-medium text-[#666] mb-1 block">COMMAND</label>
                <div className="font-mono text-xs text-[#0A0A0A] bg-white border border-[#E5E5E5] px-3 py-2 break-all">
                  {serverInfo.command} {serverInfo.args?.join(" ")}
                </div>
              </div>
              {serverInfo.github_url && (
                <div>
                  <label className="text-xs font-medium text-[#666] mb-1 block">SOURCE</label>
                  <a
                    href={serverInfo.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-xs text-[#002FA7] hover:underline break-all block"
                  >
                    {serverInfo.github_url}
                  </a>
                </div>
              )}
              <div>
                <label className="text-xs font-medium text-[#666] mb-1 block">MCP ENDPOINT</label>
                <div className="font-mono text-xs text-[#002FA7] bg-white border border-[#E5E5E5] px-3 py-2">
                  /api/servers/{serverName}/mcp/sse
                </div>
              </div>
            </div>
          </CollapsibleContent>
        </Collapsible>

        {/* Nav Tabs */}
        <div className="border-b border-[#E5E5E5]">
          <div className="px-4 py-2">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-[#666] block mb-2 px-2">Navigation</span>
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full text-left px-3 py-2 font-mono text-xs transition-colors duration-150 flex items-center gap-2 ${
                  activeTab === tab.id
                    ? "bg-[#002FA7]/5 text-[#002FA7] border-l-2 border-l-[#002FA7] font-semibold"
                    : "text-[#666] hover:text-[#0A0A0A] hover:bg-[#EBEBEB]"
                }`}
                data-testid={`nav-tab-${tab.id}`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-auto p-4 border-t border-[#E5E5E5]">
          <p className="text-[10px] font-mono text-[#999] uppercase tracking-wider text-center">MCP Protocol v1.0</p>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden border-l border-[#E5E5E5]">
        {activeTab === "tools" && (
          <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
            {/* Tool List */}
            <div className="flex-1 flex flex-col overflow-hidden bg-white">
              <div className="px-6 py-4 border-b border-[#E5E5E5]">
                <h2 className="text-sm font-bold text-[#0A0A0A] uppercase tracking-wider">Discovered Tools</h2>
              </div>
              {!isRunning ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-8 gap-3">
                  <Server className="w-10 h-10 text-[#DDD]" />
                  <p className="font-mono text-sm text-[#999]">Server is not running</p>
                  <p className="text-xs text-[#999]">Start the server to discover available tools</p>
                  <Button
                    size="sm"
                    className="bg-[#00A040] hover:bg-[#008030] text-white rounded-none text-xs font-mono mt-2"
                    onClick={() => handleStartStop("start")}
                    disabled={!!actionLoading || !serverInfo.has_credentials}
                    data-testid="start-server-inline"
                  >
                    <Play className="w-3 h-3 mr-1.5" />
                    Start Server
                  </Button>
                </div>
              ) : tools.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
                  <Loader2 className="w-6 h-6 animate-spin text-[#002FA7] mb-3" />
                  <p className="font-mono text-sm text-[#999]">No tools discovered yet</p>
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto">
                  {tools.map((tool) => (
                    <button
                      key={tool.name}
                      onClick={() => { setSelectedTool(tool); setParamValues({}); setExecResult(null); setExecError(null); }}
                      className={`w-full text-left px-6 py-3 border-b border-[#E5E5E5] hover:bg-[#F5F5F5] transition-colors ${
                        selectedTool?.name === tool.name ? "bg-[#002FA7]/5 border-l-2 border-l-[#002FA7]" : ""
                      }`}
                      data-testid={`tool-item-${tool.name}`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-semibold text-[#0A0A0A]">{tool.name}</span>
                        {tool.parameters?.length > 0 && (
                          <Badge variant="outline" className="text-[9px] font-mono px-1 py-0 text-[#666] border-[#CCC]">
                            {tool.parameters.length} params
                          </Badge>
                        )}
                      </div>
                      {tool.description && (
                        <p className="text-xs text-[#666] mt-0.5 line-clamp-2">{tool.description}</p>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Terminal Panel */}
            <div className="w-full md:w-[400px] lg:w-[500px] flex-shrink-0 bg-[#0A0A0A] text-[#00E559] flex flex-col overflow-hidden">
              <div className="px-4 py-3 border-b border-[#222] flex items-center justify-between">
                <span className="font-mono text-sm font-semibold text-[#00E559] uppercase tracking-wider">
                  {selectedTool ? selectedTool.name : "Terminal"}
                </span>
                {elapsed !== null && <span className="font-mono text-[10px] text-[#666]">{elapsed}ms</span>}
              </div>
              {selectedTool ? (
                <div className="flex-1 flex flex-col overflow-hidden">
                  {/* Parameters */}
                  {selectedTool.parameters?.length > 0 && (
                    <div className="p-4 border-b border-[#222] space-y-3 overflow-y-auto max-h-[300px]">
                      {selectedTool.parameters.map((p) => (
                        <div key={p.name}>
                          <label className="text-[10px] font-mono text-[#888] uppercase flex items-center gap-1">
                            {p.name}
                            {p.required && <span className="text-[#FF2A2A]">*</span>}
                            <span className="text-[#444]">({p.type})</span>
                          </label>
                          {p.description && <p className="text-[10px] text-[#555] mb-1">{p.description}</p>}
                          {p.enum_options?.length > 0 ? (
                            <select
                              value={paramValues[p.name] || ""}
                              onChange={(e) => setParamValues((v) => ({ ...v, [p.name]: e.target.value }))}
                              className="w-full bg-[#111] border border-[#333] text-[#E5E5E5] font-mono text-xs px-2 py-1.5"
                              data-testid={`param-select-${p.name}`}
                            >
                              <option value="">Select...</option>
                              {p.enum_options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                            </select>
                          ) : (
                            <Input
                              value={paramValues[p.name] || ""}
                              onChange={(e) => setParamValues((v) => ({ ...v, [p.name]: e.target.value }))}
                              placeholder={p.default != null ? String(p.default) : ""}
                              className="bg-[#111] border-[#333] text-[#E5E5E5] font-mono text-xs rounded-none h-7 placeholder:text-[#444]"
                              data-testid={`param-input-${p.name}`}
                            />
                          )}
                        </div>
                      ))}
                      <Button
                        size="sm"
                        className="w-full bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none text-xs font-mono"
                        onClick={() => {
                          const params = {};
                          selectedTool.parameters.forEach((p) => {
                            if (paramValues[p.name] !== undefined && paramValues[p.name] !== "") {
                              let val = paramValues[p.name];
                              if (p.type === "number" || p.type === "integer" || p.type === "int") val = Number(val);
                              else if (p.type === "boolean" || p.type === "bool") val = val === "true";
                              params[p.name] = val;
                            }
                          });
                          executeTool(selectedTool.name, params);
                        }}
                        disabled={execLoading}
                        data-testid="execute-tool-button"
                      >
                        {execLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <Play className="w-3 h-3 mr-1.5" />}
                        Execute
                      </Button>
                    </div>
                  )}
                  {/* Output */}
                  <div className="flex-1 overflow-auto p-4">
                    {execLoading && <p className="font-mono text-xs text-[#FFCC00] animate-pulse">EXECUTING...</p>}
                    {execError && (
                      <div className="p-3 border border-[#FF2A2A]/30 bg-[#FF2A2A]/5">
                        <p className="font-mono text-xs text-[#FF8A8A] whitespace-pre-wrap">{execError}</p>
                      </div>
                    )}
                    {execResult !== null && !execLoading && (
                      <pre className="font-mono text-xs leading-relaxed whitespace-pre-wrap break-all text-[#E5E5E5]" data-testid="tool-result-output">
                        {typeof execResult === "string" ? execResult : JSON.stringify(execResult, null, 2)}
                      </pre>
                    )}
                    {!execResult && !execError && !execLoading && selectedTool.parameters?.length === 0 && (
                      <Button
                        size="sm"
                        className="bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none text-xs font-mono"
                        onClick={() => executeTool(selectedTool.name, {})}
                        data-testid="execute-tool-button"
                      >
                        <Play className="w-3 h-3 mr-1.5" />
                        Execute (no params)
                      </Button>
                    )}
                    {!execResult && !execError && !execLoading && selectedTool.parameters?.length > 0 && (
                      <p className="font-mono text-xs text-[#333] text-center py-8">
                        <span className="text-[#00E559]">_</span> FILL PARAMETERS AND EXECUTE
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center">
                  <p className="font-mono text-xs text-[#333]">
                    <span className="text-[#00E559]">_</span> SELECT A TOOL TO TEST
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "apikeys" && (
          <div className="flex-1 flex flex-col overflow-hidden bg-white">
            <ApiKeyManager appName={serverName} />
          </div>
        )}
      </div>
    </div>
  );
}
