import { useState, useEffect } from "react";
import { X, Plus, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";

const PARAM_TYPES = [
  { value: "string", label: "String" },
  { value: "int", label: "Integer" },
  { value: "float", label: "Float" },
  { value: "bool", label: "Boolean" },
  { value: "enum", label: "Enum" },
  { value: "list", label: "List / Array" },
  { value: "object", label: "Object / Dict" },
];

export function ParamEditModal({ param, toolName, onSave, onClose }) {
  const isNew = !param;
  const [form, setForm] = useState({
    name: "",
    type: "string",
    required: false,
    description: "",
    default: "",
    enum_options: [],
  });
  const [enumInput, setEnumInput] = useState("");

  useEffect(() => {
    if (param) {
      setForm({
        name: param.name || "",
        type: param.type || "string",
        required: param.required ?? false,
        description: param.description || "",
        default: param.default != null ? String(param.default) : "",
        enum_options: param.enum_options || [],
      });
    }
  }, [param]);

  const handleSave = () => {
    if (!form.name.trim()) return;
    onSave({
      ...form,
      name: form.name.trim(),
      default: form.default || null,
    });
  };

  const addEnumOption = () => {
    if (!enumInput.trim()) return;
    setForm((f) => ({ ...f, enum_options: [...f.enum_options, enumInput.trim()] }));
    setEnumInput("");
  };

  const removeEnumOption = (idx) => {
    setForm((f) => ({ ...f, enum_options: f.enum_options.filter((_, i) => i !== idx) }));
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="param-edit-modal">
      <div className="bg-white border border-[#E5E5E5] shadow-lg w-full max-w-md">
        {/* Header */}
        <div className="bg-[#0A0A0A] px-5 py-3 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider">
            {isNew ? "Add Parameter" : "Edit Parameter"}
          </h3>
          <button onClick={onClose} className="text-[#666] hover:text-white" data-testid="param-modal-close">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Subtitle */}
        <div className="px-5 py-2 border-b border-[#E5E5E5] bg-[#FAFAFA]">
          <span className="text-[10px] font-mono text-[#666] uppercase tracking-wider">Tool: </span>
          <span className="text-[10px] font-mono text-[#002FA7] font-semibold">{toolName}</span>
        </div>

        {/* Form */}
        <div className="p-5 space-y-4">
          {/* Name */}
          <div>
            <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">
              Parameter Name
            </label>
            <Input
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. phone_number"
              className="rounded-none border-[#E5E5E5] font-mono text-sm"
              disabled={!isNew && param?.name}
              data-testid="param-name-input"
            />
          </div>

          {/* Type */}
          <div>
            <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">Type</label>
            <select
              value={form.type}
              onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
              className="w-full border border-[#E5E5E5] px-3 py-2 font-mono text-sm bg-white focus:border-[#002FA7] focus:outline-none"
              data-testid="param-type-select"
            >
              {PARAM_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {/* Required */}
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-[#666] uppercase tracking-wider">Required</label>
            <Switch
              checked={form.required}
              onCheckedChange={(v) => setForm((f) => ({ ...f, required: v }))}
              className="data-[state=checked]:bg-[#002FA7]"
              data-testid="param-required-switch"
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">Description</label>
            <Input
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="What this parameter does..."
              className="rounded-none border-[#E5E5E5] text-sm"
              data-testid="param-description-input"
            />
          </div>

          {/* Default */}
          <div>
            <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">Default Value</label>
            <Input
              value={form.default}
              onChange={(e) => setForm((f) => ({ ...f, default: e.target.value }))}
              placeholder="Optional default"
              className="rounded-none border-[#E5E5E5] font-mono text-sm"
              data-testid="param-default-input"
            />
          </div>

          {/* Enum Options */}
          {form.type === "enum" && (
            <div>
              <label className="text-xs font-medium text-[#666] mb-1.5 block uppercase tracking-wider">
                Enum Options
              </label>
              <div className="flex gap-2 mb-2">
                <Input
                  value={enumInput}
                  onChange={(e) => setEnumInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addEnumOption())}
                  placeholder="Add option..."
                  className="flex-1 rounded-none border-[#E5E5E5] font-mono text-sm"
                  data-testid="enum-option-input"
                />
                <Button
                  type="button"
                  onClick={addEnumOption}
                  className="bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none px-3"
                  data-testid="add-enum-option-button"
                >
                  <Plus className="w-3 h-3" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {form.enum_options.map((opt, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 bg-[#002FA7]/5 border border-[#002FA7]/20 text-[#002FA7] px-2 py-0.5 text-xs font-mono"
                  >
                    {opt}
                    <button onClick={() => removeEnumOption(i)} className="hover:text-[#FF2A2A]">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-5 py-3 border-t border-[#E5E5E5] flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} className="rounded-none font-mono text-xs" data-testid="param-cancel-button">
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!form.name.trim()}
            className="bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none font-mono text-xs"
            data-testid="param-save-button"
          >
            {isNew ? "Add Parameter" : "Save Changes"}
          </Button>
        </div>
      </div>
    </div>
  );
}
