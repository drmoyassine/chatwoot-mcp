import { useState, useRef, useEffect, useMemo } from "react";
import { Play, Trash2, Copy, Check, Loader as Loader2, TriangleAlert as AlertTriangle, Terminal, Clock, ChevronDown, FileCode as FileCode2, Braces, Pencil, Plus } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";

function syntaxHighlight(json) {
  if (typeof json !== "string") {
    json = JSON.stringify(json, null, 2);
  }
  return json
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
      function (match) {
        let cls = "json-number";
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            cls = "json-key";
          } else {
            cls = "json-string";
          }
        } else if (/true|false/.test(match)) {
          cls = "json-boolean";
        } else if (/null/.test(match)) {
          cls = "json-null";
        }
        return '<span class="' + cls + '">' + match + "</span>";
      }
    );
}

function JsonOutput({ data }) {
  const html = syntaxHighlight(data);
  return (
    <pre
      className="font-mono text-xs leading-relaxed whitespace-pre-wrap break-all text-[#E5E5E5]"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function generateCurl(tool, baseUrl, appName) {
  const isAttachment = tool.name === "create_message_with_attachment";
  const basePath = appName === "chatwoot" ? "/api/chatwoot" : `/api/servers/${appName}`;
  const endpoint = isAttachment
    ? `${baseUrl}${basePath}/tools/execute-with-file`
    : `${baseUrl}${basePath}/tools/execute`;

  if (isAttachment) {
    const paramObj = {};
    tool.parameters.forEach((p) => {
      if (p.name === "file_url") return;
      paramObj[p.name] = p.type === "int" || p.type === "integer" ? 0 : p.type === "bool" || p.type === "boolean" ? false : `<${p.name}>`;
    });
    return [
      `curl -X POST '${endpoint}' \\`,
      `  -F 'tool_name=${tool.name}' \\`,
      `  -F 'parameters=${JSON.stringify(paramObj)}' \\`,
      `  -F 'file=@/path/to/file.png'`,
    ].join("\n");
  }

  const paramObj = {};
  tool.parameters.forEach((p) => {
    if (p.type === "int" || p.type === "integer") paramObj[p.name] = 0;
    else if (p.type === "bool" || p.type === "boolean") paramObj[p.name] = false;
    else if (p.type === "list") paramObj[p.name] = [];
    else paramObj[p.name] = `<${p.name}>`;
  });

  const body = JSON.stringify({ tool_name: tool.name, parameters: paramObj }, null, 2);
  return [
    `curl -X POST '${endpoint}' \\`,
    `  -H 'Content-Type: application/json' \\`,
    `  -d '${body}'`,
  ].join("\n");
}

function ApiDocPanel({ tool, appName = "chatwoot" }) {
  const [copiedField, setCopiedField] = useState(null);
  const baseUrl = (process.env.REACT_APP_BACKEND_URL || window.location.origin).replace(/\/$/, "");

  const basePath = appName === "chatwoot" ? "/api/chatwoot" : `/api/servers/${appName}`;
  const isAttachment = tool.name === "create_message_with_attachment";
  const endpoint = isAttachment ? `${basePath}/tools/execute-with-file` : `${basePath}/tools/execute`;
  const method = "POST";
  const fullUrl = `${baseUrl}${endpoint}`;

  const curlExample = useMemo(() => generateCurl(tool, baseUrl, appName), [tool, baseUrl, appName]);

  const bodySchema = useMemo(() => {
    if (isAttachment) {
      return {
        type: "multipart/form-data",
        fields: [
          { name: "tool_name", type: "string", value: tool.name, desc: "Fixed tool identifier" },
          {
            name: "parameters",
            type: "JSON string",
            value: "{}",
            desc: "Tool parameters as JSON",
          },
          { name: "file", type: "binary", value: "(file)", desc: "File attachment" },
        ],
      };
    }
    return {
      type: "application/json",
      shape: {
        tool_name: tool.name,
        parameters: Object.fromEntries(
          tool.parameters.map((p) => [
            p.name,
            `(${p.type || "string"}${p.required ? ", required" : ""})`,
          ])
        ),
      },
    };
  }, [tool, isAttachment]);

  const copyText = (text, field) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 1500);
  };

  const CopyBtn = ({ text, field }) => (
    <button
      onClick={() => copyText(text, field)}
      className="absolute top-2 right-2 p-1 text-[#555] hover:text-[#00E559] transition-colors"
      title="Copy"
      data-testid={`copy-${field}`}
    >
      {copiedField === field ? (
        <Check className="w-3 h-3 text-[#00E559]" />
      ) : (
        <Copy className="w-3 h-3" />
      )}
    </button>
  );

  return (
    <div className="flex flex-col overflow-hidden" data-testid="api-doc-panel">
      {/* Header */}
      <div className="px-4 py-2 border-b border-[#222] flex items-center gap-2">
        <FileCode2 className="w-3.5 h-3.5 text-[#00E559]" />
        <span className="font-mono text-[10px] text-[#00E559] uppercase tracking-wider font-semibold">
          REST API Endpoint
        </span>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-3 space-y-3">
          {/* Endpoint URL */}
          <div className="relative">
            <span className="font-mono text-[10px] text-[#666] uppercase tracking-wider block mb-1">
              Endpoint
            </span>
            <div className="bg-[#111] border border-[#222] p-2 pr-8 font-mono text-xs">
              <span className="text-[#FF9500] font-bold">{method}</span>{" "}
              <span className="text-[#E5E5E5] break-all">{fullUrl}</span>
            </div>
            <CopyBtn text={fullUrl} field="url" />
          </div>

          {/* Headers */}
          <div>
            <span className="font-mono text-[10px] text-[#666] uppercase tracking-wider block mb-1">
              Headers
            </span>
            <div className="bg-[#111] border border-[#222] p-2 font-mono text-[11px] space-y-0.5">
              {isAttachment ? (
                <div>
                  <span className="text-[#888]">Content-Type:</span>{" "}
                  <span className="text-[#00BFFF]">multipart/form-data</span>
                </div>
              ) : (
                <div>
                  <span className="text-[#888]">Content-Type:</span>{" "}
                  <span className="text-[#00BFFF]">application/json</span>
                </div>
              )}
            </div>
          </div>

          {/* Request Body Schema */}
          <div className="relative">
            <span className="font-mono text-[10px] text-[#666] uppercase tracking-wider block mb-1">
              Request Body
            </span>
            {isAttachment ? (
              <div className="bg-[#111] border border-[#222] p-2 pr-8 font-mono text-[11px] space-y-1">
                {bodySchema.fields.map((f) => (
                  <div key={f.name} className="flex gap-2">
                    <span className="text-[#00E559]">{f.name}</span>
                    <span className="text-[#666]">({f.type})</span>
                    <span className="text-[#555] text-[10px]">— {f.desc}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-[#111] border border-[#222] p-2 pr-8">
                <pre className="font-mono text-[11px] text-[#E5E5E5] whitespace-pre-wrap">
                  {JSON.stringify(bodySchema.shape, null, 2)}
                </pre>
                <CopyBtn text={JSON.stringify(bodySchema.shape, null, 2)} field="body" />
              </div>
            )}
          </div>

          {/* Parameter Details */}
          {tool.parameters.length > 0 && (
            <div>
              <span className="font-mono text-[10px] text-[#666] uppercase tracking-wider block mb-1">
                Parameters
              </span>
              <div className="bg-[#111] border border-[#222] divide-y divide-[#222]">
                {tool.parameters.map((p) => (
                  <div key={p.name} className="px-2 py-1.5 flex items-start gap-2 font-mono text-[11px]">
                    <span className="text-[#00E559] flex-shrink-0">{p.name}</span>
                    <span className="text-[#666] flex-shrink-0">
                      {p.type || "string"}{p.required ? "" : "?"}
                    </span>
                    {p.description && (
                      <span className="text-[#555] text-[10px] truncate">{p.description}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* cURL Example */}
          <div className="relative">
            <span className="font-mono text-[10px] text-[#666] uppercase tracking-wider block mb-1">
              cURL Example
            </span>
            <div className="bg-[#111] border border-[#222] p-2 pr-8">
              <pre className="font-mono text-[11px] text-[#E5E5E5] whitespace-pre-wrap break-all">
                {curlExample}
              </pre>
            </div>
            <CopyBtn text={curlExample} field="curl" />
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}

export function TestTerminal({ selectedTool, onExecute, onExecuteWithFile, connectionStatus, onEditParam, onAddParam, appName = "chatwoot" }) {
  const [params, setParams] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(null);
  const [copied, setCopied] = useState(false);
  const [history, setHistory] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const outputRef = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => {
    if (selectedTool) {
      const defaults = {};
      selectedTool.parameters.forEach((p) => {
        if (p.default !== undefined && p.default !== null) {
          defaults[p.name] = p.default;
        } else {
          defaults[p.name] = "";
        }
      });
      setParams(defaults);
      setResult(null);
      setError(null);
      setElapsed(null);
      setSelectedFile(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  }, [selectedTool]);

  const isAttachmentTool = selectedTool?.name === "create_message_with_attachment";

  const handleExecute = async () => {
    if (!selectedTool) return;
    setLoading(true);
    setError(null);
    setResult(null);
    const start = performance.now();
    try {
      const cleanParams = {};
      for (const [key, val] of Object.entries(params)) {
        if (val === "" || val === undefined) continue;
        // Skip file_url param if we have a direct file upload
        if (isAttachmentTool && key === "file_url" && selectedFile) continue;
        const paramDef = selectedTool.parameters.find((p) => p.name === key);
        if (paramDef) {
          if (paramDef.type === "int" || paramDef.type === "integer") {
            cleanParams[key] = parseInt(val, 10);
          } else if (paramDef.type === "bool" || paramDef.type === "boolean") {
            cleanParams[key] = val === true || val === "true";
          } else if (paramDef.type === "list") {
            try {
              cleanParams[key] = JSON.parse(val);
            } catch {
              cleanParams[key] = val.split(",").map((s) => s.trim());
            }
          } else {
            cleanParams[key] = val;
          }
        } else {
          cleanParams[key] = val;
        }
      }

      let resp;
      if (isAttachmentTool && selectedFile && onExecuteWithFile) {
        resp = await onExecuteWithFile(selectedTool.name, cleanParams, selectedFile);
      } else {
        resp = await onExecute(selectedTool.name, cleanParams);
      }
      const duration = Math.round(performance.now() - start);
      setResult(resp.result);
      setElapsed(duration);
      setHistory((prev) => [
        { tool: selectedTool.name, params: cleanParams, result: resp.result, duration, ts: new Date() },
        ...prev.slice(0, 19),
      ]);
    } catch (e) {
      const duration = Math.round(performance.now() - start);
      setElapsed(duration);
      setError(e.response?.data?.detail || e.message || "Execution failed");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    const text = JSON.stringify(result || error, null, 2);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClear = () => {
    setResult(null);
    setError(null);
    setElapsed(null);
  };

  const handleParamChange = (name, value) => {
    setParams((prev) => ({ ...prev, [name]: value }));
  };

  const [activePane, setActivePane] = useState("execute");

  return (
    <div
      className="terminal-panel w-full md:w-[400px] lg:w-[500px] flex-shrink-0 bg-[#0A0A0A] text-[#00E559] flex flex-col overflow-hidden relative"
      data-testid="test-terminal"
    >
      {/* Scanline overlay */}
      <div className="terminal-scanline" />

      {/* Tab Header */}
      <div className="relative z-10 px-2 py-0 border-b border-[#222] flex items-center justify-between">
        <div className="flex items-center">
          <button
            onClick={() => setActivePane("execute")}
            className={`px-3 py-2.5 font-mono text-xs uppercase tracking-wider flex items-center gap-1.5 border-b-2 transition-colors ${
              activePane === "execute"
                ? "text-[#00E559] border-[#00E559]"
                : "text-[#555] border-transparent hover:text-[#888]"
            }`}
            data-testid="tab-live-testing"
          >
            <Terminal className="w-3.5 h-3.5" />
            Live Testing
          </button>
          <button
            onClick={() => setActivePane("docs")}
            className={`px-3 py-2.5 font-mono text-xs uppercase tracking-wider flex items-center gap-1.5 border-b-2 transition-colors ${
              activePane === "docs"
                ? "text-[#00E559] border-[#00E559]"
                : "text-[#555] border-transparent hover:text-[#888]"
            }`}
            data-testid="tab-api-docs"
          >
            <FileCode2 className="w-3.5 h-3.5" />
            API Docs
          </button>
        </div>
        <div className="flex items-center gap-2 pr-1">
          {activePane === "execute" && elapsed !== null && (
            <span className="font-mono text-[10px] text-[#666] flex items-center gap-1" data-testid="execution-time">
              <Clock className="w-3 h-3" />
              {elapsed}ms
            </span>
          )}
          {activePane === "execute" && (
            <>
              <button
                onClick={handleClear}
                className="text-[#666] hover:text-[#999] transition-colors"
                title="Clear output"
                data-testid="clear-output-button"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleCopy}
                className="text-[#666] hover:text-[#999] transition-colors"
                title="Copy output"
                data-testid="copy-output-button"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-[#00E559]" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="relative z-10 flex-1 flex flex-col overflow-hidden">
        {!selectedTool ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="text-center">
              <Terminal className="w-10 h-10 text-[#333] mx-auto mb-3" />
              <p className="font-mono text-sm text-[#444]">SELECT A TOOL TO BEGIN</p>
              <p className="font-mono text-xs text-[#333] mt-1">Choose from the Tool Explorer panel</p>
            </div>
          </div>
        ) : activePane === "execute" ? (
          <>
            {/* Tool Name */}
            <div className="px-4 py-2 border-b border-[#222]">
              <span className="font-mono text-xs text-[#666]">TOOL &gt; </span>
              <span className="font-mono text-sm text-[#00E559] font-semibold" data-testid="selected-tool-name">
                {selectedTool.name}
              </span>
            </div>

            {/* Parameters */}
            {selectedTool.parameters.length > 0 && (
              <div className="px-4 py-3 border-b border-[#222] space-y-2 max-h-[240px] overflow-y-auto">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[10px] text-[#666] uppercase tracking-wider">
                    Parameters
                  </span>
                  {onAddParam && (
                    <button
                      onClick={() => onAddParam(selectedTool)}
                      className="text-[#555] hover:text-[#00E559] transition-colors"
                      title="Add parameter"
                      data-testid="terminal-add-param"
                    >
                      <Plus className="w-3 h-3" />
                    </button>
                  )}
                </div>
                {selectedTool.parameters.map((p) => (
                  <div key={p.name} className="flex items-center gap-2 group/param">
                    <label className="font-mono text-xs text-[#888] w-32 flex-shrink-0 truncate flex items-center gap-1" title={p.name}>
                      {p.name}
                      {p.required && <span className="text-[#FF2A2A] ml-0.5">*</span>}
                      }
                      {onEditParam && (
                        <Pencil
                          className="w-2.5 h-2.5 opacity-0 group-hover/param:opacity-100 text-[#555] hover:text-[#00E559] cursor-pointer transition-opacity"
                          onClick={() => onEditParam(selectedTool, p)}
                          data-testid={`terminal-edit-param-${p.name}`}
                        />
                      )}
                    </label>
                    {p.type === "bool" || p.type === "boolean" ? (
                      <Switch
                        checked={params[p.name] === true || params[p.name] === "true"}
                        onCheckedChange={(v) => handleParamChange(p.name, v)}
                        className="data-[state=checked]:bg-[#002FA7]"
                        data-testid={`param-input-${p.name}`}
                      />
                    ) : p.type === "enum" && p.enum_options?.length > 0 ? (
                      <select
                        value={params[p.name] ?? ""}
                        onChange={(e) => handleParamChange(p.name, e.target.value)}
                        className="flex-1 bg-[#151515] border border-[#333] text-[#E5E5E5] font-mono text-xs px-2 py-1.5 focus:border-[#00E559] focus:outline-none"
                        data-testid={`param-input-${p.name}`}
                      >
                        <option value="">Select...</option>
                        {p.enum_options.map((opt) => (
                          <option key={opt} value={opt}>{opt}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        value={params[p.name] ?? ""}
                        onChange={(e) => handleParamChange(p.name, e.target.value)}
                        placeholder={p.type || "string"}
                        className="flex-1 bg-[#151515] border border-[#333] text-[#E5E5E5] font-mono text-xs px-2 py-1.5 focus:border-[#00E559] focus:outline-none transition-colors placeholder:text-[#444]"
                        data-testid={`param-input-${p.name}`}
                      />
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* File Upload for Attachment tools */}
            {isAttachmentTool && (
              <div className="px-4 py-2 border-b border-[#222]">
                <span className="font-mono text-[10px] text-[#666] uppercase tracking-wider block mb-2">
                  File Attachment
                </span>
                <div className="flex items-center gap-2">
                  <input
                    ref={fileRef}
                    type="file"
                    onChange={(e) => setSelectedFile(e.target.files[0] || null)}
                    className="flex-1 font-mono text-xs text-[#E5E5E5] file:mr-2 file:py-1 file:px-3 file:border file:border-[#333] file:text-[10px] file:font-mono file:bg-[#151515] file:text-[#00E559] file:cursor-pointer hover:file:bg-[#222]"
                    data-testid="file-upload-input"
                  />
                </div>
                {selectedFile && (
                  <p className="font-mono text-[10px] text-[#00E559] mt-1">
                    {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)}KB)
                  </p>
                )}
                <p className="font-mono text-[10px] text-[#444] mt-1">
                  Upload a file directly, or use file_url param for remote files
                </p>
              </div>
            )}

            {/* Execute Button */}
            <div className="px-4 py-2 border-b border-[#222]">
              <Button
                onClick={handleExecute}
                disabled={loading || connectionStatus !== "connected"}
                className="w-full bg-[#002FA7] hover:bg-[#001B66] text-white font-mono text-xs uppercase tracking-wider rounded-none h-9 disabled:opacity-40"
                data-testid="live-test-execute-button"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" />
                    EXECUTING...
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 mr-2" />
                    EXECUTE
                  </>
                )}
              </Button>
              {connectionStatus !== "connected" && (
                <p className="font-mono text-[10px] text-[#FF2A2A] mt-1 text-center">
                  Server not connected
                </p>
              )}
            </div>

            {/* Output */}
            <ScrollArea className="flex-1" ref={outputRef}>
              <div className="p-4">
                {error && (
                  <div className="mb-3 p-3 border border-[#FF2A2A]/30 bg-[#FF2A2A]/5" data-testid="error-output">
                    <div className="flex items-center gap-2 mb-1">
                      <AlertTriangle className="w-3.5 h-3.5 text-[#FF2A2A]" />
                      <span className="font-mono text-xs text-[#FF2A2A] font-semibold uppercase">Error</span>
                    </div>
                    <p className="font-mono text-xs text-[#FF8A8A] whitespace-pre-wrap">{error}</p>
                  </div>
                )}
                {result !== null && (
                  <div className="font-mono text-xs leading-relaxed" data-testid="json-output">
                    <JsonOutput data={result} />
                  </div>
                )}
                {!error && result === null && !loading && (
                  <div className="text-center py-8">
                    <p className="font-mono text-xs text-[#333]">
                      <span className="cursor-blink text-[#00E559]">_</span>
                      {" "}READY
                    </p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </>
        ) : (
          /* API Documentation Pane */
          <ApiDocPanel tool={selectedTool} appName={appName} />
        )}
      </div>

      {/* History */}
      {history.length > 0 && activePane === "execute" && (
        <details className="relative z-10 border-t border-[#222]">
          <summary className="px-4 py-2 cursor-pointer font-mono text-[10px] text-[#666] uppercase tracking-wider hover:text-[#999] flex items-center gap-1.5">
            <ChevronDown className="w-3 h-3" />
            History ({history.length})
          </summary>
          <div className="max-h-[120px] overflow-y-auto border-t border-[#222]">
            {history.map((h, i) => (
              <button
                key={i}
                onClick={() => {
                  setResult(h.result);
                  setElapsed(h.duration);
                  setError(null);
                }}
                className="w-full text-left px-4 py-1.5 font-mono text-[10px] hover:bg-[#151515] flex items-center justify-between"
              >
                <span className="text-[#00E559] truncate">{h.tool}</span>
                <span className="text-[#666] flex-shrink-0 ml-2">{h.duration}ms</span>
              </button>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
