import { useState, useRef, useEffect } from "react";
import {
  Play,
  Trash2,
  Copy,
  Check,
  Loader2,
  AlertTriangle,
  Terminal,
  Clock,
  ChevronDown,
} from "lucide-react";
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

export function TestTerminal({ selectedTool, onExecute, onExecuteWithFile, connectionStatus }) {
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

  return (
    <div
      className="terminal-panel w-full md:w-[400px] lg:w-[500px] flex-shrink-0 bg-[#0A0A0A] text-[#00E559] flex flex-col overflow-hidden relative"
      data-testid="test-terminal"
    >
      {/* Scanline overlay */}
      <div className="terminal-scanline" />

      {/* Header */}
      <div className="relative z-10 px-4 py-3 border-b border-[#222] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-[#00E559]" />
          <h3 className="font-mono text-sm font-semibold text-[#00E559] uppercase tracking-wider">
            Live Testing
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {elapsed !== null && (
            <span className="font-mono text-[10px] text-[#666] flex items-center gap-1" data-testid="execution-time">
              <Clock className="w-3 h-3" />
              {elapsed}ms
            </span>
          )}
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
        ) : (
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
                <span className="font-mono text-[10px] text-[#666] uppercase tracking-wider block mb-2">
                  Parameters
                </span>
                {selectedTool.parameters.map((p) => (
                  <div key={p.name} className="flex items-center gap-2">
                    <label className="font-mono text-xs text-[#888] w-32 flex-shrink-0 truncate" title={p.name}>
                      {p.name}
                      {p.required && <span className="text-[#FF2A2A] ml-0.5">*</span>}
                    </label>
                    {p.type === "bool" || p.type === "boolean" ? (
                      <Switch
                        checked={params[p.name] === true || params[p.name] === "true"}
                        onCheckedChange={(v) => handleParamChange(p.name, v)}
                        className="data-[state=checked]:bg-[#002FA7]"
                        data-testid={`param-input-${p.name}`}
                      />
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
                  Connect to Chatwoot first
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
        )}
      </div>

      {/* History */}
      {history.length > 0 && (
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
