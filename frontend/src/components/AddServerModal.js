import { useState } from "react";
import { X, Upload, Loader2, GitBranch, AlertCircle, Check, Server, Plus, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { useAuth } from "@/contexts/AuthContext";

export function AddServerModal({ onClose, onAdded }) {
  const { axiosAuth } = useAuth();
  const [step, setStep] = useState("url"); // url | preview | installing | credentials
  const [githubUrl, setGithubUrl] = useState("");
  const [parseError, setParseError] = useState("");
  const [parsing, setParsing] = useState(false);
  const [serverInfo, setServerInfo] = useState(null);
  const [installing, setInstalling] = useState(false);
  const [installError, setInstallError] = useState("");
  const [credentialInputs, setCredentialInputs] = useState({});
  const [savingCreds, setSavingCreds] = useState(false);

  const api = axiosAuth();

  const handleParse = async () => {
    if (!githubUrl.trim()) return;
    setParsing(true);
    setParseError("");
    try {
      const resp = await api.post("/api/servers/parse-github", { github_url: githubUrl.trim() });
      const info = resp.data.server_info;
      // Add default credentials schema based on known servers
      if (!info.credentials_schema || info.credentials_schema.length === 0) {
        info.credentials_schema = inferCredentialsSchema(info.name, info.npm_package || info.pip_package);
      }
      setServerInfo(info);
      setStep("preview");
    } catch (e) {
      setParseError(e.response?.data?.detail || "Failed to parse GitHub URL");
    } finally {
      setParsing(false);
    }
  };

  const handleInstall = async () => {
    setInstalling(true);
    setInstallError("");
    try {
      await api.post("/api/servers/add", {
        github_url: githubUrl,
        name: serverInfo.name,
        display_name: serverInfo.display_name || serverInfo.name.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        description: serverInfo.description || `MCP server for ${serverInfo.name}`,
        runtime: serverInfo.runtime,
        command: serverInfo.command,
        args: serverInfo.args,
        npm_package: serverInfo.npm_package || "",
        pip_package: serverInfo.pip_package || "",
        credentials_schema: serverInfo.credentials_schema || [],
      });
      if (serverInfo.credentials_schema && serverInfo.credentials_schema.length > 0) {
        setStep("credentials");
      } else {
        onAdded();
        onClose();
      }
    } catch (e) {
      setInstallError(e.response?.data?.detail || "Installation failed");
    } finally {
      setInstalling(false);
    }
  };

  const handleSaveCredentials = async () => {
    setSavingCreds(true);
    try {
      await api.post(`/api/servers/${serverInfo.name}/credentials`, {
        credentials: credentialInputs,
      });
      // Try to start the server
      try {
        await api.post(`/api/servers/${serverInfo.name}/start`);
      } catch {
        // Server might fail to start if creds are wrong — that's OK
      }
      onAdded();
      onClose();
    } catch (e) {
      setInstallError(e.response?.data?.detail || "Failed to save credentials");
    } finally {
      setSavingCreds(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="add-server-modal">
      <div className="bg-white border border-[#E5E5E5] shadow-lg w-full max-w-lg max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="bg-[#0A0A0A] px-5 py-3 flex items-center justify-between flex-shrink-0">
          <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center gap-2">
            <Server className="w-4 h-4" />
            {step === "url" ? "Add MCP Server" : step === "preview" ? "Confirm Installation" : step === "credentials" ? "Configure Credentials" : "Installing..."}
          </h3>
          <button onClick={onClose} className="text-[#666] hover:text-white" data-testid="add-server-close">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {step === "url" && (
            <div className="p-5 space-y-4">
              <p className="text-sm text-[#666]">
                Paste the <strong>GitHub repository URL</strong> of an MCP server.
                The package will be automatically detected and installed.
              </p>
              <div>
                <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">
                  GitHub Repository URL
                </label>
                <Input
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/modelcontextprotocol/servers/tree/main/src/github"
                  className="rounded-none border-[#E5E5E5] font-mono text-sm"
                  onKeyDown={(e) => e.key === "Enter" && handleParse()}
                  data-testid="github-url-input"
                />
              </div>
              {parseError && (
                <div className="flex items-center gap-2 text-xs text-[#FF2A2A] bg-[#FF2A2A]/5 border border-[#FF2A2A]/20 px-3 py-2" data-testid="parse-error">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                  {parseError}
                </div>
              )}
              <div className="bg-[#F9F9F9] border border-[#E5E5E5] p-3 text-xs text-[#888]">
                <p className="font-semibold text-[#666] mb-1">Supported formats:</p>
                <code className="block text-[10px] font-mono mb-0.5">https://github.com/org/repo</code>
                <code className="block text-[10px] font-mono">https://github.com/org/repo/tree/main/src/server-name</code>
              </div>
            </div>
          )}

          {step === "preview" && serverInfo && (
            <div className="p-5 space-y-4">
              {/* Detected info */}
              <div className="bg-[#002FA7]/5 border border-[#002FA7]/20 p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-[#002FA7]" />
                  <span className="font-mono text-sm font-bold text-[#002FA7]">{serverInfo.name}</span>
                  <Badge variant="outline" className="text-[10px] font-mono px-1.5 text-[#002FA7] border-[#002FA7]/30">
                    {serverInfo.runtime}
                  </Badge>
                </div>
                <div className="space-y-1 text-xs font-mono">
                  <div><span className="text-[#666]">Package:</span> <span className="text-[#0A0A0A]">{serverInfo.npm_package || serverInfo.pip_package}</span></div>
                  <div><span className="text-[#666]">Command:</span> <span className="text-[#0A0A0A]">{serverInfo.command} {serverInfo.args?.join(" ")}</span></div>
                  <div><span className="text-[#666]">Source:</span> <span className="text-[#0A0A0A] break-all">{serverInfo.github_url}</span></div>
                </div>
              </div>

              {/* Editable fields */}
              <div>
                <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">Server Name</label>
                <Input
                  value={serverInfo.name}
                  onChange={(e) => setServerInfo((s) => ({ ...s, name: e.target.value }))}
                  className="rounded-none border-[#E5E5E5] font-mono text-sm"
                  data-testid="server-name-input"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">Description</label>
                <Input
                  value={serverInfo.description || ""}
                  onChange={(e) => setServerInfo((s) => ({ ...s, description: e.target.value }))}
                  placeholder="What this server does..."
                  className="rounded-none border-[#E5E5E5] text-sm"
                  data-testid="server-description-input"
                />
              </div>

              {/* Editable Credentials / Environment Variables */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-medium text-[#666] uppercase tracking-wider">
                    Environment Variables
                  </label>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-[10px] font-mono text-[#002FA7] hover:bg-[#002FA7]/5 rounded-none px-2"
                    onClick={() => {
                      const schema = [...(serverInfo.credentials_schema || [])];
                      schema.push({ key: "", label: "", required: false, hint: "" });
                      setServerInfo((s) => ({ ...s, credentials_schema: schema }));
                    }}
                    data-testid="add-env-var-button"
                  >
                    <Plus className="w-3 h-3 mr-1" />
                    Add Variable
                  </Button>
                </div>
                {serverInfo.credentials_schema?.length > 0 ? (
                  <div className="bg-[#FAFAFA] border border-[#E5E5E5] divide-y divide-[#E5E5E5]">
                    {serverInfo.credentials_schema.map((cs, idx) => (
                      <div key={idx} className="px-3 py-2.5 space-y-2">
                        <div className="flex items-center gap-2">
                          <Input
                            value={cs.key}
                            onChange={(e) => {
                              const schema = [...serverInfo.credentials_schema];
                              schema[idx] = { ...schema[idx], key: e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, "") };
                              if (!schema[idx].label || schema[idx].label === cs.key) {
                                schema[idx].label = e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, "");
                              }
                              setServerInfo((s) => ({ ...s, credentials_schema: schema }));
                            }}
                            placeholder="ENV_VAR_NAME"
                            className="flex-1 rounded-none border-[#E5E5E5] font-mono text-xs h-7"
                            data-testid={`env-key-${idx}`}
                          />
                          <div className="flex items-center gap-1.5 flex-shrink-0">
                            <Switch
                              checked={cs.required}
                              onCheckedChange={(checked) => {
                                const schema = [...serverInfo.credentials_schema];
                                schema[idx] = { ...schema[idx], required: checked };
                                setServerInfo((s) => ({ ...s, credentials_schema: schema }));
                              }}
                              className="scale-75"
                              data-testid={`env-required-${idx}`}
                            />
                            <span className="text-[9px] font-mono text-[#999] w-12">{cs.required ? "REQ" : "OPT"}</span>
                          </div>
                          <button
                            onClick={() => {
                              const schema = serverInfo.credentials_schema.filter((_, i) => i !== idx);
                              setServerInfo((s) => ({ ...s, credentials_schema: schema }));
                            }}
                            className="text-[#CCC] hover:text-[#FF2A2A] transition-colors flex-shrink-0"
                            data-testid={`env-remove-${idx}`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <Input
                          value={cs.label || ""}
                          onChange={(e) => {
                            const schema = [...serverInfo.credentials_schema];
                            schema[idx] = { ...schema[idx], label: e.target.value };
                            setServerInfo((s) => ({ ...s, credentials_schema: schema }));
                          }}
                          placeholder="Description (e.g. API URL for self-hosted instance)"
                          className="rounded-none border-[#E5E5E5] text-[11px] h-7 text-[#666]"
                          data-testid={`env-label-${idx}`}
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-[#FAFAFA] border border-[#E5E5E5] px-3 py-4 text-center">
                    <p className="text-[11px] text-[#999]">No environment variables configured</p>
                    <p className="text-[10px] text-[#BBB] mt-0.5">Add any API keys, URLs, or tokens this server needs</p>
                  </div>
                )}
                <p className="text-[10px] text-[#999] mt-1">You'll set the values after installation. Add any env vars the server needs.</p>
              </div>

              {installError && (
                <div className="flex items-center gap-2 text-xs text-[#FF2A2A] bg-[#FF2A2A]/5 border border-[#FF2A2A]/20 px-3 py-2">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                  {installError}
                </div>
              )}
            </div>
          )}

          {step === "credentials" && serverInfo && (
            <div className="p-5 space-y-4">
              <div className="flex items-center gap-2 text-sm text-[#00A040]">
                <Check className="w-4 h-4" />
                <span className="font-semibold">Server installed successfully!</span>
              </div>
              <p className="text-sm text-[#666]">
                Enter the required credentials. These will be <strong>encrypted at rest</strong> in the database.
              </p>
              {serverInfo.credentials_schema?.map((cs) => (
                <div key={cs.key}>
                  <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">
                    {cs.label || cs.key}
                    {cs.required && <span className="text-[#FF2A2A] ml-1">*</span>}
                  </label>
                  <Input
                    type="password"
                    value={credentialInputs[cs.key] || ""}
                    onChange={(e) => setCredentialInputs((c) => ({ ...c, [cs.key]: e.target.value }))}
                    placeholder={`Enter ${cs.label || cs.key}...`}
                    className="rounded-none border-[#E5E5E5] font-mono text-sm"
                    data-testid={`credential-input-${cs.key}`}
                  />
                  {cs.hint && <p className="text-[10px] text-[#999] mt-1">{cs.hint}</p>}
                </div>
              ))}
              {installError && (
                <div className="flex items-center gap-2 text-xs text-[#FF2A2A] bg-[#FF2A2A]/5 border border-[#FF2A2A]/20 px-3 py-2">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                  {installError}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[#E5E5E5] flex justify-between flex-shrink-0">
          {step !== "url" && step !== "credentials" && (
            <Button variant="outline" onClick={() => setStep("url")} className="rounded-none font-mono text-xs">
              Back
            </Button>
          )}
          <div className="flex gap-2 ml-auto">
            <Button variant="outline" onClick={onClose} className="rounded-none font-mono text-xs">
              Cancel
            </Button>
            {step === "url" && (
              <Button
                onClick={handleParse}
                disabled={parsing || !githubUrl.trim()}
                className="bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none font-mono text-xs"
                data-testid="parse-github-button"
              >
                {parsing ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <GitBranch className="w-3.5 h-3.5 mr-1" />}
                Detect Package
              </Button>
            )}
            {step === "preview" && (
              <Button
                onClick={handleInstall}
                disabled={installing}
                className="bg-[#00A040] hover:bg-[#008030] text-white rounded-none font-mono text-xs"
                data-testid="install-server-button"
              >
                {installing ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Upload className="w-3.5 h-3.5 mr-1" />}
                {installing ? "Installing..." : "Install Server"}
              </Button>
            )}
            {step === "credentials" && (
              <Button
                onClick={handleSaveCredentials}
                disabled={savingCreds}
                className="bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none font-mono text-xs"
                data-testid="save-credentials-button"
              >
                {savingCreds ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}
                Save & Connect
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


/**
 * Infer common credentials based on known MCP server names.
 */
function inferCredentialsSchema(name, pkg) {
  const known = {
    github: [{ key: "GITHUB_PERSONAL_ACCESS_TOKEN", label: "GitHub Personal Access Token", required: true, hint: "Create at github.com/settings/tokens" }],
    gitlab: [{ key: "GITLAB_PERSONAL_ACCESS_TOKEN", label: "GitLab Access Token", required: true }, { key: "GITLAB_API_URL", label: "GitLab API URL", required: false }],
    slack: [{ key: "SLACK_BOT_TOKEN", label: "Slack Bot Token", required: true }, { key: "SLACK_TEAM_ID", label: "Slack Team ID", required: true }],
    "google-drive": [{ key: "GOOGLE_DRIVE_CREDENTIALS", label: "Google Drive Credentials JSON", required: true }],
    postgres: [{ key: "POSTGRES_CONNECTION_STRING", label: "PostgreSQL Connection String", required: true }],
    sqlite: [{ key: "SQLITE_DB_PATH", label: "SQLite Database Path", required: true }],
    "brave-search": [{ key: "BRAVE_API_KEY", label: "Brave Search API Key", required: true }],
    filesystem: [{ key: "ALLOWED_DIRECTORIES", label: "Allowed Directories (comma-separated)", required: true }],
    memory: [],
    fetch: [],
    puppeteer: [],
    firecrawl: [{ key: "FIRECRAWL_API_KEY", label: "Firecrawl API Key", required: true, hint: "Get from firecrawl.dev" }],
    stripe: [{ key: "STRIPE_API_KEY", label: "Stripe API Key", required: true }],
    sentry: [{ key: "SENTRY_AUTH_TOKEN", label: "Sentry Auth Token", required: true }, { key: "SENTRY_ORGANIZATION", label: "Sentry Organization Slug", required: true }],
  };

  const lowerName = (name || "").toLowerCase();
  for (const [k, v] of Object.entries(known)) {
    if (lowerName.includes(k)) return v;
  }

  // Default: ask for a generic API key
  return [{ key: "API_KEY", label: "API Key", required: false, hint: "Check the server's README for required environment variables" }];
}
