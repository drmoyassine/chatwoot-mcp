import { useState } from "react";
import { X, Upload, Loader2, Plus, Pencil, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { ParamEditModal } from "./ParamEditModal";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export function CreateToolModal({ categories, onClose, onCreated }) {
  const { axiosAuth } = useAuth();
  const [step, setStep] = useState("input"); // input | preview
  const [schema, setSchema] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState("");
  const [tool, setTool] = useState(null);
  const [newCategory, setNewCategory] = useState("");
  const [saving, setSaving] = useState(false);
  const [editParam, setEditParam] = useState(null); // null or index
  const [showAddParam, setShowAddParam] = useState(false);

  const api = axiosAuth();

  const handleParse = async () => {
    if (!schema.trim()) return;
    setParsing(true);
    setParseError("");
    try {
      const resp = await api.post("/api/chatwoot/tools/parse-schema", { schema: schema.trim() });
      setTool(resp.data.tool);
      setStep("preview");
    } catch (e) {
      setParseError(e.response?.data?.detail || "Failed to parse schema");
    } finally {
      setParsing(false);
    }
  };

  const handleSave = async () => {
    if (!tool || !tool.name.trim()) return;
    setSaving(true);
    try {
      const category = newCategory.trim() || tool.category || "custom";
      await api.post("/api/chatwoot/tools/create", {
        name: tool.name,
        description: tool.description,
        category,
        parameters: tool.parameters,
        source_schema: schema,
      });
      onCreated();
      onClose();
    } catch (e) {
      setParseError(e.response?.data?.detail || "Failed to create tool");
    } finally {
      setSaving(false);
    }
  };

  const updateParam = (idx, updated) => {
    setTool((t) => ({
      ...t,
      parameters: t.parameters.map((p, i) => (i === idx ? updated : p)),
    }));
    setEditParam(null);
  };

  const addParam = (newParam) => {
    setTool((t) => ({ ...t, parameters: [...t.parameters, newParam] }));
    setShowAddParam(false);
  };

  const removeParam = (idx) => {
    setTool((t) => ({ ...t, parameters: t.parameters.filter((_, i) => i !== idx) }));
  };

  const allCategories = [...new Set([...categories.filter((c) => c !== "all"), "custom"])];

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="create-tool-modal">
      <div className="bg-white border border-[#E5E5E5] shadow-lg w-full max-w-2xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="bg-[#0A0A0A] px-5 py-3 flex items-center justify-between flex-shrink-0">
          <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider">
            {step === "input" ? "Create New Tool" : "Preview & Configure"}
          </h3>
          <button onClick={onClose} className="text-[#666] hover:text-white" data-testid="create-tool-close">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {step === "input" ? (
            <div className="p-5 space-y-4">
              <p className="text-sm text-[#666]">
                Paste a <strong>cURL command</strong> or <strong>JSON request body</strong> from API documentation.
                Auth headers and account_id will be automatically stripped.
              </p>
              <textarea
                value={schema}
                onChange={(e) => setSchema(e.target.value)}
                placeholder={`curl --request PUT \\
  --url https://app.chatwoot.com/api/v1/accounts/{account_id}/contacts/{id} \\
  --header 'Content-Type: application/json' \\
  --data '{ "name": "Alice", "email": "alice@acme.inc" }'`}
                className="w-full h-48 border border-[#E5E5E5] p-3 font-mono text-xs bg-[#FAFAFA] focus:border-[#002FA7] focus:outline-none resize-none"
                data-testid="schema-input"
              />
              {parseError && (
                <p className="text-xs text-[#FF2A2A] bg-[#FF2A2A]/5 border border-[#FF2A2A]/20 px-3 py-2" data-testid="parse-error">
                  {parseError}
                </p>
              )}
            </div>
          ) : (
            <div className="p-5 space-y-4">
              {/* Tool Name */}
              <div>
                <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">Tool Name</label>
                <Input
                  value={tool.name}
                  onChange={(e) => setTool((t) => ({ ...t, name: e.target.value }))}
                  className="rounded-none border-[#E5E5E5] font-mono text-sm"
                  data-testid="tool-name-input"
                />
              </div>

              {/* Description */}
              <div>
                <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">Description</label>
                <textarea
                  value={tool.description}
                  onChange={(e) => setTool((t) => ({ ...t, description: e.target.value }))}
                  placeholder="What this tool does..."
                  className="w-full border border-[#E5E5E5] p-3 text-sm focus:border-[#002FA7] focus:outline-none resize-none h-16"
                  data-testid="tool-description-input"
                />
              </div>

              {/* Category */}
              <div>
                <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">Category</label>
                <div className="flex gap-2">
                  <select
                    value={newCategory || tool.category || "custom"}
                    onChange={(e) => {
                      if (e.target.value === "__new__") {
                        setNewCategory("");
                      } else {
                        setNewCategory(e.target.value);
                        setTool((t) => ({ ...t, category: e.target.value }));
                      }
                    }}
                    className="flex-1 border border-[#E5E5E5] px-3 py-2 font-mono text-sm bg-white focus:border-[#002FA7] focus:outline-none"
                    data-testid="tool-category-select"
                  >
                    {allCategories.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                    <option value="__new__">+ New Category</option>
                  </select>
                  {newCategory === "" && (
                    <Input
                      value={newCategory}
                      onChange={(e) => setNewCategory(e.target.value)}
                      placeholder="Category name"
                      className="flex-1 rounded-none border-[#E5E5E5] font-mono text-sm"
                    />
                  )}
                </div>
              </div>

              {/* Method & Path */}
              {tool.method && (
                <div className="flex gap-2">
                  <div className="w-24">
                    <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">Method</label>
                    <select
                      value={tool.method}
                      onChange={(e) => setTool((t) => ({ ...t, method: e.target.value }))}
                      className="w-full border border-[#E5E5E5] px-3 py-2 font-mono text-sm bg-white focus:border-[#002FA7] focus:outline-none"
                      data-testid="tool-method-select"
                    >
                      {["GET", "POST", "PUT", "PATCH", "DELETE"].map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex-1">
                    <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">API Path</label>
                    <Input
                      value={tool.path}
                      onChange={(e) => setTool((t) => ({ ...t, path: e.target.value }))}
                      placeholder="/contacts/{id}"
                      className="rounded-none border-[#E5E5E5] font-mono text-sm"
                      data-testid="tool-path-input"
                    />
                  </div>
                </div>
              )}

              {/* Parameters */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-[#666] uppercase tracking-wider">
                    Parameters ({tool.parameters.length})
                  </label>
                  <Button
                    type="button"
                    onClick={() => setShowAddParam(true)}
                    className="bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none font-mono text-[10px] h-7 px-2"
                    data-testid="add-param-button"
                  >
                    <Plus className="w-3 h-3 mr-1" />
                    Add Param
                  </Button>
                </div>
                <div className="border border-[#E5E5E5] divide-y divide-[#E5E5E5]">
                  {tool.parameters.map((p, i) => (
                    <div key={i} className="px-3 py-2 flex items-center gap-2 text-xs group hover:bg-[#FAFAFA]">
                      <span className="font-mono font-semibold text-[#0A0A0A] w-32 truncate">{p.name}</span>
                      <span className="font-mono text-[#666] w-16">{p.type}</span>
                      <span className={`text-[10px] ${p.required ? "text-[#002FA7]" : "text-[#999]"}`}>
                        {p.required ? "required" : "optional"}
                      </span>
                      <span className="flex-1 text-[#888] truncate text-[10px]">{p.description}</span>
                      <button
                        onClick={() => setEditParam(i)}
                        className="opacity-0 group-hover:opacity-100 text-[#666] hover:text-[#002FA7] transition-opacity"
                        data-testid={`edit-param-${p.name}`}
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => removeParam(i)}
                        className="opacity-0 group-hover:opacity-100 text-[#666] hover:text-[#FF2A2A] transition-opacity"
                        data-testid={`delete-param-${p.name}`}
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                  {tool.parameters.length === 0 && (
                    <p className="px-3 py-4 text-xs text-[#999] text-center">No parameters defined</p>
                  )}
                </div>
              </div>

              {parseError && (
                <p className="text-xs text-[#FF2A2A] bg-[#FF2A2A]/5 border border-[#FF2A2A]/20 px-3 py-2" data-testid="save-error">
                  {parseError}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[#E5E5E5] flex justify-between flex-shrink-0">
          {step === "preview" && (
            <Button variant="outline" onClick={() => setStep("input")} className="rounded-none font-mono text-xs">
              Back
            </Button>
          )}
          <div className="flex gap-2 ml-auto">
            <Button variant="outline" onClick={onClose} className="rounded-none font-mono text-xs">
              Cancel
            </Button>
            {step === "input" ? (
              <Button
                onClick={handleParse}
                disabled={parsing || !schema.trim()}
                className="bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none font-mono text-xs"
                data-testid="parse-schema-button"
              >
                {parsing ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Upload className="w-3.5 h-3.5 mr-1" />}
                Parse Schema
              </Button>
            ) : (
              <Button
                onClick={handleSave}
                disabled={saving || !tool?.name?.trim()}
                className="bg-[#00A040] hover:bg-[#008030] text-white rounded-none font-mono text-xs"
                data-testid="save-tool-button"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}
                Save Tool
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Sub-modals */}
      {editParam !== null && tool && (
        <ParamEditModal
          param={tool.parameters[editParam]}
          toolName={tool.name}
          onSave={(updated) => updateParam(editParam, updated)}
          onClose={() => setEditParam(null)}
        />
      )}
      {showAddParam && tool && (
        <ParamEditModal
          param={null}
          toolName={tool.name}
          onSave={addParam}
          onClose={() => setShowAddParam(false)}
        />
      )}
    </div>
  );
}
