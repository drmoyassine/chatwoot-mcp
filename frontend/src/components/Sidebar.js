import { useState } from "react";
import {
  Settings,
  Wifi,
  WifiOff,
  Loader2,
  AlertCircle,
  Server,
  Terminal,
  Radio,
  ChevronDown,
  ChevronRight,
  Save,
  Zap,
  Eye,
  EyeOff,
  ArrowLeft,
  LogOut,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

export function Sidebar({
  config,
  connectionStatus,
  accountName,
  mcpInfo,
  onSaveConfig,
  onTestConnection,
  activeTab,
  onTabChange,
  tabs,
  outputFormat,
  onOutputFormatChange,
  onBack,
  onLogout,
}) {
  const [isConfigOpen, setIsConfigOpen] = useState(true);
  const [isMcpOpen, setIsMcpOpen] = useState(true);
  const [editConfig, setEditConfig] = useState(null);
  const [showToken, setShowToken] = useState(false);
  const isEditing = editConfig !== null;

  const startEdit = () => {
    setEditConfig({
      chatwoot_url: config.chatwoot_url,
      api_token: "",
      account_id: config.account_id,
    });
  };

  const cancelEdit = () => {
    setEditConfig(null);
    setShowToken(false);
  };

  const handleSave = () => {
    if (editConfig.chatwoot_url && editConfig.api_token && editConfig.account_id) {
      onSaveConfig(editConfig);
      setEditConfig(null);
      setShowToken(false);
    }
  };

  const statusIcon = {
    connected: <Wifi className="w-3.5 h-3.5 text-[#00E559]" />,
    testing: <Loader2 className="w-3.5 h-3.5 text-[#FFCC00] animate-spin" />,
    error: <AlertCircle className="w-3.5 h-3.5 text-[#FF2A2A]" />,
    disconnected: <WifiOff className="w-3.5 h-3.5 text-[#999999]" />,
  };

  const statusLabel = {
    connected: "CONNECTED",
    testing: "TESTING...",
    error: "ERROR",
    disconnected: "OFFLINE",
  };

  const statusColor = {
    connected: "bg-[#00E559]/10 text-[#00E559] border-[#00E559]/20",
    testing: "bg-[#FFCC00]/10 text-[#FFCC00] border-[#FFCC00]/20",
    error: "bg-[#FF2A2A]/10 text-[#FF2A2A] border-[#FF2A2A]/20",
    disconnected: "bg-[#999]/10 text-[#666] border-[#999]/20",
  };

  return (
    <aside
      className="w-full md:w-80 flex-shrink-0 bg-[#F5F5F5] border-r border-[#E5E5E5] flex flex-col overflow-y-auto"
      data-testid="sidebar"
    >
      {/* Header */}
      <div className="p-6 border-b border-[#E5E5E5]">
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-xs text-[#666] hover:text-[#002FA7] font-mono mb-3 transition-colors"
            data-testid="sidebar-back-button"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            All Servers
          </button>
        )}
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 bg-[#002FA7] flex items-center justify-center">
            <Server className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="font-heading text-lg font-bold tracking-tight text-[#0A0A0A]" data-testid="app-title">
              Chatwoot MCP
            </h1>
            <p className="text-xs text-[#666] font-mono">MODEL CONTEXT PROTOCOL</p>
          </div>
          {onLogout && (
            <button
              onClick={onLogout}
              className="text-[#999] hover:text-[#FF2A2A] transition-colors"
              title="Logout"
              data-testid="sidebar-logout-button"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
        <div className="flex items-center gap-2 mt-3">
          {statusIcon[connectionStatus]}
          <Badge
            variant="outline"
            className={`text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 border ${statusColor[connectionStatus]}`}
            data-testid="connection-status-badge"
          >
            {statusLabel[connectionStatus]}
          </Badge>
          {accountName && (
            <span className="text-xs text-[#666] truncate" data-testid="account-name">
              {accountName}
            </span>
          )}
        </div>
      </div>

      {/* Configuration Section */}
      <Collapsible open={isConfigOpen} onOpenChange={setIsConfigOpen}>
        <CollapsibleTrigger className="w-full flex items-center justify-between px-6 py-3 border-b border-[#E5E5E5] hover:bg-[#EBEBEB] transition-colors duration-150">
          <span className="text-xs font-bold uppercase tracking-[0.2em] text-[#666]">
            <Settings className="w-3.5 h-3.5 inline mr-2" />
            Configuration
          </span>
          {isConfigOpen ? (
            <ChevronDown className="w-4 h-4 text-[#666]" />
          ) : (
            <ChevronRight className="w-4 h-4 text-[#666]" />
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="p-4 space-y-3 border-b border-[#E5E5E5]">
            {!isEditing ? (
              <>
                <div>
                  <label className="text-xs font-medium text-[#666] mb-1 block">INSTANCE URL</label>
                  <div className="font-mono text-sm text-[#0A0A0A] bg-white border border-[#E5E5E5] px-3 py-2 truncate" data-testid="config-display-url">
                    {config.chatwoot_url || "Not configured"}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-[#666] mb-1 block">API TOKEN</label>
                  <div className="font-mono text-sm text-[#0A0A0A] bg-white border border-[#E5E5E5] px-3 py-2" data-testid="config-display-token">
                    {config.api_token || "Not set"}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-[#666] mb-1 block">ACCOUNT ID</label>
                  <div className="font-mono text-sm text-[#0A0A0A] bg-white border border-[#E5E5E5] px-3 py-2" data-testid="config-display-account-id">
                    {config.account_id || "Not set"}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 bg-transparent border-[#0A0A0A] text-[#0A0A0A] hover:bg-[#E5E5E5] font-medium rounded-none text-xs"
                    onClick={startEdit}
                    data-testid="config-edit-button"
                  >
                    <Settings className="w-3 h-3 mr-1.5" />
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    className="flex-1 bg-[#002FA7] text-white hover:bg-[#001B66] font-medium rounded-none text-xs"
                    onClick={onTestConnection}
                    data-testid="config-test-button"
                  >
                    <Zap className="w-3 h-3 mr-1.5" />
                    Test
                  </Button>
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="text-xs font-medium text-[#0A0A0A] mb-1 block">INSTANCE URL</label>
                  <Input
                    value={editConfig.chatwoot_url}
                    onChange={(e) => setEditConfig({ ...editConfig, chatwoot_url: e.target.value })}
                    placeholder="https://app.chatwoot.com"
                    className="font-mono text-sm rounded-none border-[#E5E5E5] focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7]"
                    data-testid="config-input-url"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-[#0A0A0A] mb-1 block">API TOKEN</label>
                  <div className="relative">
                    <Input
                      type={showToken ? "text" : "password"}
                      value={editConfig.api_token}
                      onChange={(e) => setEditConfig({ ...editConfig, api_token: e.target.value })}
                      placeholder="Enter access token"
                      className="font-mono text-sm rounded-none border-[#E5E5E5] focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7] pr-10"
                      data-testid="config-input-token"
                    />
                    <button
                      type="button"
                      onClick={() => setShowToken(!showToken)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-[#666] hover:text-[#0A0A0A]"
                    >
                      {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-[#0A0A0A] mb-1 block">ACCOUNT ID</label>
                  <Input
                    type="number"
                    value={editConfig.account_id}
                    onChange={(e) => setEditConfig({ ...editConfig, account_id: e.target.value })}
                    placeholder="1"
                    className="font-mono text-sm rounded-none border-[#E5E5E5] focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7]"
                    data-testid="config-input-account-id"
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 rounded-none text-xs"
                    onClick={cancelEdit}
                    data-testid="config-cancel-button"
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    className="flex-1 bg-[#002FA7] text-white hover:bg-[#001B66] rounded-none text-xs"
                    onClick={handleSave}
                    data-testid="config-save-button"
                  >
                    <Save className="w-3 h-3 mr-1.5" />
                    Save
                  </Button>
                </div>
              </>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* MCP Server Info */}
      <Collapsible open={isMcpOpen} onOpenChange={setIsMcpOpen}>
        <CollapsibleTrigger className="w-full flex items-center justify-between px-6 py-3 border-b border-[#E5E5E5] hover:bg-[#EBEBEB] transition-colors duration-150">
          <span className="text-xs font-bold uppercase tracking-[0.2em] text-[#666]">
            <Radio className="w-3.5 h-3.5 inline mr-2" />
            MCP Server
          </span>
          {isMcpOpen ? (
            <ChevronDown className="w-4 h-4 text-[#666]" />
          ) : (
            <ChevronRight className="w-4 h-4 text-[#666]" />
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="p-4 space-y-3 border-b border-[#E5E5E5]">
            <div>
              <label className="text-xs font-medium text-[#666] mb-1 block">SSE ENDPOINT</label>
              <div className="font-mono text-xs text-[#0A0A0A] bg-white border border-[#E5E5E5] px-3 py-2 break-all" data-testid="mcp-sse-endpoint">
                {mcpInfo?.transport?.sse?.endpoint || "/api/mcp/sse"}
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-[#666] mb-1 block">STDIO COMMAND</label>
              <div className="font-mono text-xs text-[#0A0A0A] bg-white border border-[#E5E5E5] px-3 py-2" data-testid="mcp-stdio-command">
                <Terminal className="w-3 h-3 inline mr-1.5 text-[#666]" />
                {mcpInfo?.transport?.stdio?.command || "python mcp_stdio.py"}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[#666]">Registered Tools</span>
              <span className="font-mono text-sm font-bold text-[#002FA7]" data-testid="mcp-tools-count">
                {mcpInfo?.tools_count || 0}
              </span>
            </div>
            <div>
              <label className="text-xs font-medium text-[#666] mb-1.5 block">DISCOVERY OUTPUT FORMAT</label>
              <div className="flex border border-[#E5E5E5] bg-white" data-testid="output-format-toggle">
                <button
                  onClick={() => onOutputFormatChange && onOutputFormatChange("json")}
                  className={`flex-1 font-mono text-xs py-1.5 px-3 transition-colors ${
                    outputFormat === "json"
                      ? "bg-[#002FA7] text-white"
                      : "text-[#666] hover:bg-[#F0F0F0]"
                  }`}
                  data-testid="output-format-json"
                >
                  JSON
                </button>
                <button
                  onClick={() => onOutputFormatChange && onOutputFormatChange("toon")}
                  className={`flex-1 font-mono text-xs py-1.5 px-3 transition-colors border-l border-[#E5E5E5] ${
                    outputFormat === "toon"
                      ? "bg-[#002FA7] text-white"
                      : "text-[#666] hover:bg-[#F0F0F0]"
                  }`}
                  data-testid="output-format-toon"
                >
                  TOON
                </button>
              </div>
              <p className="text-[10px] text-[#999] mt-1">
                {outputFormat === "toon" ? "Compact format — ~40% fewer tokens for discovery tools" : "Standard JSON format for discovery tool outputs"}
              </p>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Navigation Tabs */}
      {tabs && (
        <div className="border-b border-[#E5E5E5]">
          <div className="px-4 py-2">
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-[#666] block mb-2 px-2">
              Navigation
            </span>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
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
      )}

      {/* Footer */}
      <div className="mt-auto p-4 border-t border-[#E5E5E5]">
        <p className="text-[10px] font-mono text-[#999] uppercase tracking-wider text-center">
          MCP Protocol v1.0
        </p>
      </div>
    </aside>
  );
}
