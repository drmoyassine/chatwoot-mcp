import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { Sidebar } from "@/components/Sidebar";
import { ToolExplorer } from "@/components/ToolExplorer";
import { TestTerminal } from "@/components/TestTerminal";
import { FilterBuilder } from "@/components/FilterBuilder";
import { WebhookEvents } from "@/components/WebhookEvents";
import { ApiKeyManager } from "@/components/ApiKeyManager";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function FilterTab({ executeTool, connectionStatus }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(null);

  const handleExecute = async (toolName, parameters) => {
    setLoading(true);
    setError(null);
    setResult(null);
    const start = performance.now();
    try {
      const resp = await executeTool(toolName, parameters);
      setResult(resp.result);
      setElapsed(Math.round(performance.now() - start));
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Filter failed");
      setElapsed(Math.round(performance.now() - start));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
      <div className="flex-1 p-6 overflow-y-auto bg-white">
        <FilterBuilder onExecute={handleExecute} loading={loading} connectionStatus={connectionStatus} />
      </div>
      <div className="terminal-panel w-full md:w-[400px] lg:w-[500px] flex-shrink-0 bg-[#0A0A0A] text-[#00E559] flex flex-col overflow-hidden relative">
        <div className="terminal-scanline" />
        <div className="relative z-10 px-4 py-3 border-b border-[#222] flex items-center justify-between">
          <span className="font-mono text-sm font-semibold text-[#00E559] uppercase tracking-wider">Filter Results</span>
          {elapsed !== null && <span className="font-mono text-[10px] text-[#666]">{elapsed}ms</span>}
        </div>
        <div className="relative z-10 flex-1 overflow-auto p-4">
          {loading && <p className="font-mono text-xs text-[#FFCC00] animate-pulse">FILTERING...</p>}
          {error && (
            <div className="p-3 border border-[#FF2A2A]/30 bg-[#FF2A2A]/5">
              <p className="font-mono text-xs text-[#FF8A8A] whitespace-pre-wrap">{error}</p>
            </div>
          )}
          {result !== null && !loading && (
            <pre
              className="font-mono text-xs leading-relaxed whitespace-pre-wrap break-all text-[#E5E5E5]"
              data-testid="filter-result-output"
              dangerouslySetInnerHTML={{
                __html: (() => {
                  const json = JSON.stringify(result, null, 2);
                  return json
                    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
                    .replace(
                      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
                      (match) => {
                        let cls = "json-number";
                        if (/^"/.test(match)) { cls = /:$/.test(match) ? "json-key" : "json-string"; }
                        else if (/true|false/.test(match)) { cls = "json-boolean"; }
                        else if (/null/.test(match)) { cls = "json-null"; }
                        return `<span class="${cls}">${match}</span>`;
                      }
                    );
                })(),
              }}
            />
          )}
          {!result && !error && !loading && (
            <p className="font-mono text-xs text-[#333] text-center py-8">
              <span className="cursor-blink text-[#00E559]">_</span> BUILD AND EXECUTE A FILTER
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ChatwootDashboard() {
  const { axiosAuth, logout } = useAuth();
  const navigate = useNavigate();
  const [config, setConfig] = useState({ chatwoot_url: "", api_token: "", account_id: "" });
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [accountName, setAccountName] = useState("");
  const [tools, setTools] = useState([]);
  const [selectedTool, setSelectedTool] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [mcpInfo, setMcpInfo] = useState(null);
  const [activeTab, setActiveTab] = useState("tools");
  const [outputFormat, setOutputFormat] = useState("json");

  const api = useCallback(() => axiosAuth(), [axiosAuth]);

  const testConnection = useCallback(async () => {
    setConnectionStatus("testing");
    try {
      const resp = await api().post("/api/chatwoot/config/test");
      setConnectionStatus("connected");
      setAccountName(resp.data.account_name || "");
    } catch (e) {
      setConnectionStatus("error");
      setAccountName("");
    }
  }, [api]);

  const fetchConfig = useCallback(async () => {
    try {
      const resp = await api().get("/api/chatwoot/config");
      const data = resp.data;
      setConfig({
        chatwoot_url: data.chatwoot_url || "",
        api_token: data.api_token_masked || "",
        account_id: data.account_id || "",
      });
      if (data.api_token_set) testConnection();
    } catch (e) {
      console.error("Failed to fetch config", e);
    }
  }, [api, testConnection]);

  const fetchTools = useCallback(async () => {
    try {
      const resp = await api().get("/api/chatwoot/tools");
      setTools(resp.data.tools || []);
    } catch (e) {
      console.error("Failed to fetch tools", e);
    }
  }, [api]);

  const fetchMcpInfo = useCallback(async () => {
    try {
      const resp = await api().get("/api/chatwoot/mcp/info");
      setMcpInfo(resp.data);
    } catch (e) {
      console.error("Failed to fetch MCP info", e);
    }
  }, [api]);

  const fetchOutputFormat = useCallback(async () => {
    try {
      const resp = await api().get("/api/chatwoot/config/output-format");
      setOutputFormat(resp.data.output_format || "json");
    } catch (e) {
      console.error("Failed to fetch output format", e);
    }
  }, [api]);

  useEffect(() => {
    fetchConfig();
    fetchTools();
    fetchMcpInfo();
    fetchOutputFormat();
  }, [fetchConfig, fetchTools, fetchMcpInfo, fetchOutputFormat]);

  const handleOutputFormatChange = async (fmt) => {
    try {
      await api().post("/api/chatwoot/config/output-format", { output_format: fmt });
      setOutputFormat(fmt);
    } catch (e) {
      console.error("Failed to save output format", e);
    }
  };

  const saveConfig = async (newConfig) => {
    try {
      await api().post("/api/chatwoot/config", {
        chatwoot_url: newConfig.chatwoot_url,
        api_token: newConfig.api_token,
        account_id: parseInt(newConfig.account_id, 10),
      });
      setConfig(newConfig);
      await testConnection();
    } catch (e) {
      console.error("Failed to save config", e);
    }
  };

  const executeTool = async (toolName, parameters) => {
    const resp = await api().post("/api/chatwoot/tools/execute", { tool_name: toolName, parameters });
    return resp.data;
  };

  const executeToolWithFile = async (toolName, parameters, file) => {
    const formData = new FormData();
    formData.append("tool_name", toolName);
    formData.append("parameters", JSON.stringify(parameters));
    if (file) formData.append("file", file);
    const resp = await api().post("/api/chatwoot/tools/execute-with-file", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return resp.data;
  };

  const categories = ["all", ...new Set(tools.map((t) => t.category))].sort();
  const filteredTools = tools.filter((t) => {
    const matchesCategory = selectedCategory === "all" || t.category === selectedCategory;
    const matchesSearch = !searchQuery || t.name.toLowerCase().includes(searchQuery.toLowerCase()) || t.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const TABS = [
    { id: "tools", label: "Tools" },
    { id: "filters", label: "Filters" },
    { id: "webhooks", label: "Webhooks" },
    { id: "apikeys", label: "API Keys" },
  ];

  return (
    <div className="h-screen w-full flex flex-col md:flex-row overflow-hidden" data-testid="chatwoot-dashboard">
      <Sidebar
        config={config}
        connectionStatus={connectionStatus}
        accountName={accountName}
        mcpInfo={mcpInfo}
        onSaveConfig={saveConfig}
        onTestConnection={testConnection}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        tabs={TABS}
        outputFormat={outputFormat}
        onOutputFormatChange={handleOutputFormatChange}
        onBack={() => navigate("/dashboard")}
        onLogout={handleLogout}
      />
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden border-l border-[#E5E5E5]">
        {activeTab === "tools" && (
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
            />
            <TestTerminal
              selectedTool={selectedTool}
              onExecute={executeTool}
              onExecuteWithFile={executeToolWithFile}
              connectionStatus={connectionStatus}
            />
          </>
        )}
        {activeTab === "filters" && <FilterTab executeTool={executeTool} connectionStatus={connectionStatus} />}
        {activeTab === "webhooks" && (
          <div className="flex-1 flex flex-col overflow-hidden bg-white">
            <WebhookEvents />
          </div>
        )}
        {activeTab === "apikeys" && (
          <div className="flex-1 flex flex-col overflow-hidden bg-white">
            <ApiKeyManager appName="chatwoot" />
          </div>
        )}
      </div>
    </div>
  );
}
