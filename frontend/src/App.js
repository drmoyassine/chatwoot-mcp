import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Sidebar } from "@/components/Sidebar";
import { ToolExplorer } from "@/components/ToolExplorer";
import { TestTerminal } from "@/components/TestTerminal";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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

  const categories = ["all", ...new Set(tools.map((t) => t.category))].sort();

  const filteredTools = tools.filter((t) => {
    const matchesCategory = selectedCategory === "all" || t.category === selectedCategory;
    const matchesSearch =
      !searchQuery ||
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="h-screen w-full flex flex-col md:flex-row overflow-hidden" data-testid="app-container">
      <Sidebar
        config={config}
        connectionStatus={connectionStatus}
        accountName={accountName}
        mcpInfo={mcpInfo}
        onSaveConfig={saveConfig}
        onTestConnection={testConnection}
      />
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden border-l border-[#E5E5E5]">
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
          connectionStatus={connectionStatus}
        />
      </div>
    </div>
  );
}

export default App;
