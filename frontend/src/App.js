import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Sidebar } from "@/components/Sidebar";
import { ToolExplorer } from "@/components/ToolExplorer";
import { TestTerminal } from "@/components/TestTerminal";
import { FilterBuilder } from "@/components/FilterBuilder";
import { WebhookEvents } from "@/components/WebhookEvents";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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
        <FilterBuilder
          onExecute={handleExecute}
          loading={loading}
          connectionStatus={connectionStatus}
        />
      </div>
      <div className="terminal-panel w-full md:w-[400px] lg:w-[500px] flex-shrink-0 bg-[#0A0A0A] text-[#00E559] flex flex-col overflow-hidden relative">
        <div className="terminal-scanline" />
        <div className="relative z-10 px-4 py-3 border-b border-[#222] flex items-center justify-between">
          <span className="font-mono text-sm font-semibold text-[#00E559] uppercase tracking-wider">
            Filter Results
          </span>
          {elapsed !== null && (
            <span className="font-mono text-[10px] text-[#666]">{elapsed}ms</span>
          )}
        </div>
        <div className="relative z-10 flex-1 overflow-auto p-4">
          {loading && (
            <p className="font-mono text-xs text-[#FFCC00] animate-pulse">FILTERING...</p>
          )}
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

function App() {
  const [config, setConfig] = useState({
    chatwoot_url: "",
    api_token: "",
    account_id: "",
  });
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [accountName, setAccountName] = useState("");
  const [tools, setTools] = useState([]);
  const [selectedTool, setSelectedTool] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [mcpInfo, setMcpInfo] = useState(null);
  const [activeTab, setActiveTab] = useState("tools"); // tools | filters | webhooks

  const fetchConfig = useCallback(async () => {
    try {
      const resp = await axios.get(`${API}/config`);
      const data = resp.data;
      setConfig({
        chatwoot_url: data.chatwoot_url || "",
        api_token: data.api_token_masked || "",
        account_id: data.account_id || "",
      });
      if (data.api_token_set) {
        testConnection();
      }
    } catch (e) {
      console.error("Failed to fetch config", e);
    }
  }, []);

  const fetchTools = useCallback(async () => {
    try {
      const resp = await axios.get(`${API}/tools`);
      setTools(resp.data.tools || []);
    } catch (e) {
      console.error("Failed to fetch tools", e);
    }
  }, []);

  const fetchMcpInfo = useCallback(async () => {
    try {
      const resp = await axios.get(`${API}/mcp/info`);
      setMcpInfo(resp.data);
    } catch (e) {
      console.error("Failed to fetch MCP info", e);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
    fetchTools();
    fetchMcpInfo();
  }, [fetchConfig, fetchTools, fetchMcpInfo]);

  const testConnection = async () => {
    setConnectionStatus("testing");
    try {
      const resp = await axios.post(`${API}/config/test`);
      setConnectionStatus("connected");
      setAccountName(resp.data.account_name || "");
    } catch (e) {
      setConnectionStatus("error");
      setAccountName("");
    }
  };

  const saveConfig = async (newConfig) => {
    try {
      await axios.post(`${API}/config`, {
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
    const resp = await axios.post(`${API}/tools/execute`, {
      tool_name: toolName,
      parameters,
    });
    return resp.data;
  };

  const executeToolWithFile = async (toolName, parameters, file) => {
    const formData = new FormData();
    formData.append("tool_name", toolName);
    formData.append("parameters", JSON.stringify(parameters));
    if (file) formData.append("file", file);
    const resp = await axios.post(`${API}/tools/execute-with-file`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return resp.data;
  };

  const categories = ["all", ...new Set(tools.map((t) => t.category))].sort();

  const filteredTools = tools.filter((t) => {
    const matchesCategory = selectedCategory === "all" || t.category === selectedCategory;
    const matchesSearch =
      !searchQuery ||
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const TABS = [
    { id: "tools", label: "Tools" },
    { id: "filters", label: "Filters" },
    { id: "webhooks", label: "Webhooks" },
  ];

  return (
    <div className="h-screen w-full flex flex-col md:flex-row overflow-hidden" data-testid="app-container">
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
        {activeTab === "filters" && (
          <FilterTab
            executeTool={executeTool}
            connectionStatus={connectionStatus}
          />
        )}
        {activeTab === "webhooks" && (
          <div className="flex-1 flex flex-col overflow-hidden bg-white">
            <WebhookEvents />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
