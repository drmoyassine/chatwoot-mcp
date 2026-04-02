import { useState } from "react";
import { FilterBuilder } from "@/components/FilterBuilder";

export function FilterTab({ executeTool, connectionStatus }) {
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
          {elapsed !== null ? <span className="font-mono text-[10px] text-[#666]">{elapsed}ms</span> : null}
          }
        </div>
        <div className="relative z-10 flex-1 overflow-auto p-4">
          {loading ? <p className="font-mono text-xs text-[#FFCC00] animate-pulse">FILTERING...</p> : null}
          }
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
