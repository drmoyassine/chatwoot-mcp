import { useState } from "react";
import {
  Settings,
  Wifi,
  WifiOff,
  Loader2,
  Server,
  Radio,
  ChevronDown,
  Save,
  Eye,
  EyeOff,
  ArrowLeft,
  LogOut,
  Play,
  Square,
  RefreshCw,
  Plus,
  GitBranch,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

export function Sidebar({
  serverInfo,
  serverName,
  isRunning,
  toolsCount,
  credentials,
  onSaveCredentials,
  savingCreds,
  activeTab,
  onTabChange,
  tabs,
  outputFormat,
  onOutputFormatChange,
  onBack,
  onLogout,
  onStartStop,
  onRestart,
  actionLoading,
}) {
  const [editingCreds, setEditingCreds] = useState(false);
  const [credInputs, setCredInputs] = useState({});
  const [showValues, setShowValues] = useState({});
  const [newEnvKey, setNewEnvKey] = useState("");
  const [localSchema, setLocalSchema] = useState(null);

  const schema = localSchema || serverInfo?.credentials_schema || [];
  const hasCredentials = serverInfo?.has_credentials || false;

  const handleSave = () => {
    onSaveCredentials(credInputs, schema);
    setEditingCreds(false);
    setCredInputs({});
    setNewEnvKey("");
    setLocalSchema(null);
  };

  const handleCancel = () => {
    setEditingCreds(false);
    setCredInputs({});
    setNewEnvKey("");
    setLocalSchema(null);
  };

  return (
    <aside
      className="w-full md:w-80 flex-shrink-0 bg-[#F5F5F5] border-r border-[#E5E5E5] flex flex-col overflow-y-auto"
      data-testid="sidebar"
    >
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
          <div className="w-8 h-8 bg-[#0A0A0A] flex items-center justify-center">
            <GitBranch className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-lg font-bold tracking-tight text-[#0A0A0A] truncate" data-testid="server-title">
              {serverInfo?.display_name || serverName}
            </h1>
            <p className="text-xs text-[#666] font-mono uppercase">
              {serverInfo?.runtime || "node"} MCP SERVER
            </p>
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
          {isRunning ? (
            <Wifi className="w-3.5 h-3.5 text-[#00E559]" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-[#999]" />
          )}
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
          {isRunning && toolsCount > 0 && (
            <span className="text-xs text-[#666] font-mono">{toolsCount} tools</span>
          )}
        </div>

        <div className="flex gap-2 mt-4">
          {isRunning ? (
            <Button
              size="sm"
              className="flex-1 bg-[#FF2A2A] hover:bg-[#CC0000] text-white rounded-none text-xs font-mono"
              onClick={() => onStartStop("stop")}
              disabled={!!actionLoading}
              data-testid="stop-server-button"
            >
              {actionLoading === "stop" ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
              ) : (
                <Square className="w-3 h-3 mr-1.5" />
              )}
              Stop
            </Button>
          ) : (
            <Button
              size="sm"
              className="flex-1 bg-[#00A040] hover:bg-[#008030] text-white rounded-none text-xs font-mono"
              onClick={() => onStartStop("start")}
              disabled={!!actionLoading || !hasCredentials}
              data-testid="start-server-button"
              title={!hasCredentials ? "Configure credentials first" : ""}
            >
              {actionLoading === "start" ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
              ) : (
                <Play className="w-3 h-3 mr-1.5" />
              )}
              Start
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            className="rounded-none text-xs font-mono"
            onClick={onRestart}
            disabled={!!actionLoading || !isRunning}
            data-testid="restart-server-button"
          >
            {actionLoading === "restart" ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5" />
            )}
          </Button>
        </div>
      </div>

      <Collapsible defaultOpen={!hasCredentials}>
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
                {schema.length > 0 ? (
                  schema.map((cs) => (
                    <div key={cs.key}>
                      <label className="text-xs font-medium text-[#666] mb-1 block uppercase">
                        {cs.label || cs.key}
                      </label>
                      <div className="font-mono text-sm text-[#0A0A0A] bg-white border border-[#E5E5E5] px-3 py-2 flex items-center justify-between">
                        <span className="truncate" data-testid={`cred-display-${cs.key}`}>
                          {credentials[cs.key] || (hasCredentials ? "***" : "Not set")}
                        </span>
                        {credentials[cs.key] && (
                          <button
                            onClick={() =>
                              setShowValues((v) => ({ ...v, [cs.key]: !v[cs.key] }))
                            }
                            className="text-[#666] hover:text-[#0A0A0A] ml-2"
                          >
                            {showValues[cs.key] ? (
                              <EyeOff className="w-3.5 h-3.5" />
                            ) : (
                              <Eye className="w-3.5 h-3.5" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div>
                    <label className="text-xs font-medium text-[#666] mb-1 block">STATUS</label>
                    <div className="font-mono text-sm text-[#0A0A0A] bg-white border border-[#E5E5E5] px-3 py-2">
                      {hasCredentials ? "Configured" : "No credentials saved"}
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
                  {hasCredentials ? "Update Credentials" : "Configure Credentials"}
                </Button>
              </>
            ) : (
              <>
                {(schema.length > 0
                  ? schema
                  : [{ key: "API_KEY", label: "API Key", required: false }]
                ).map((cs) => (
                  <div key={cs.key}>
                    <label className="text-xs font-medium text-[#0A0A0A] mb-1 block uppercase">
                      {cs.label || cs.key}
                      {cs.required ? <span className="text-[#FF2A2A] ml-1">*</span> : null}
                    </label>
                    <Input
                      type="password"
                      value={credInputs[cs.key] || ""}
                      onChange={(e) =>
                        setCredInputs((c) => ({ ...c, [cs.key]: e.target.value }))
                      }
                      placeholder={`Enter ${cs.label || cs.key}...`}
                      className="rounded-none border-[#E5E5E5] font-mono text-sm"
                      data-testid={`cred-input-${cs.key}`}
                    />
                    {cs.hint ? <p className="text-[10px] text-[#999] mt-1">{cs.hint}</p> : null}
                  </div>
                ))}

                <div className="pt-2 border-t border-dashed border-[#E5E5E5]">
                  <label className="text-[10px] font-medium text-[#999] mb-1.5 block uppercase tracking-wider">
                    Add custom environment variable
                  </label>
                  <div className="flex gap-2">
                    <Input
                      value={newEnvKey}
                      onChange={(e) =>
                        setNewEnvKey(e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, ""))
                      }
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
                        const updated = [...schema];
                        if (!updated.find((s) => s.key === key)) {
                          updated.push({ key, label: key, required: false });
                          setLocalSchema(updated);
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
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 rounded-none text-xs"
                    onClick={handleCancel}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    className="flex-1 bg-[#002FA7] text-white hover:bg-[#001B66] rounded-none text-xs"
                    onClick={handleSave}
                    disabled={savingCreds}
                    data-testid="save-credentials-button"
                  >
                    {savingCreds ? (
                      <Loader2 className="w-3 h-3 animate-spin mr-1" />
                    ) : (
                      <Save className="w-3 h-3 mr-1.5" />
                    )}
                    Save
                  </Button>
                </div>
              </>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>

      <Collapsible defaultOpen>
        <CollapsibleTrigger className="w-full flex items-center justify-between px-6 py-3 border-b border-[#E5E5E5] hover:bg-[#EBEBEB] transition-colors duration-150">
          <span className="text-xs font-bold uppercase tracking-[0.2em] text-[#666]">
            <Radio className="w-3.5 h-3.5 inline mr-2" />
            MCP Server
          </span>
          <ChevronDown className="w-4 h-4 text-[#666]" />
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="p-4 space-y-3 border-b border-[#E5E5E5]">
            <div>
              <label className="text-xs font-medium text-[#666] mb-1 block">SSE ENDPOINT</label>
              <div className="font-mono text-xs text-[#002FA7] bg-white border border-[#E5E5E5] px-3 py-2 break-all">
                /api/servers/{serverName}/mcp/sse
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-[#666] mb-1 block">COMMAND</label>
              <div className="font-mono text-xs text-[#0A0A0A] bg-white border border-[#E5E5E5] px-3 py-2 break-all">
                {serverInfo?.command} {serverInfo?.args?.join(" ")}
              </div>
            </div>
            {serverInfo?.github_url && (
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
            <div className="flex items-center justify-between">
              <span className="text-xs text-[#666]">Registered Tools</span>
              <span className="font-mono text-sm font-bold text-[#002FA7]" data-testid="mcp-tools-count">
                {toolsCount}
              </span>
            </div>
            <div>
              <label className="text-xs font-medium text-[#666] mb-1.5 block">
                DISCOVERY OUTPUT FORMAT
              </label>
              <div className="flex border border-[#E5E5E5] bg-white" data-testid="output-format-toggle">
                <button
                  onClick={() => onOutputFormatChange("json")}
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
                  onClick={() => onOutputFormatChange("toon")}
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
                {outputFormat === "toon"
                  ? "Compact format -- ~40% fewer tokens for discovery tools"
                  : "Standard JSON format for discovery tool outputs"}
              </p>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>

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

      <div className="mt-auto p-4 border-t border-[#E5E5E5]">
        <p className="text-[10px] font-mono text-[#999] uppercase tracking-wider text-center">
          MCP Protocol v1.0
        </p>
      </div>
    </aside>
  );
}
