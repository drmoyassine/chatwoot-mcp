import { useState } from "react";
import {
  Plus,
  Trash2,
  Play,
  Loader2,
  Filter,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const ATTRIBUTE_OPTIONS = [
  { value: "status", label: "Status", type: "select", options: ["open", "resolved", "pending", "snoozed"] },
  { value: "assignee_id", label: "Assignee ID", type: "number" },
  { value: "inbox_id", label: "Inbox ID", type: "number" },
  { value: "team_id", label: "Team ID", type: "number" },
  { value: "labels", label: "Labels", type: "text" },
  { value: "priority", label: "Priority", type: "select", options: ["none", "low", "medium", "high", "urgent"] },
  { value: "display_id", label: "Display ID", type: "number" },
  { value: "browser_language", label: "Browser Language", type: "text" },
  { value: "country_code", label: "Country Code", type: "text" },
  { value: "city", label: "City", type: "text" },
  { value: "created_at", label: "Created At", type: "text" },
  { value: "last_activity_at", label: "Last Activity At", type: "text" },
  { value: "referer", label: "Referer URL", type: "text" },
  { value: "campaign_id", label: "Campaign ID", type: "number" },
  { value: "contact_identifier", label: "Contact Identifier", type: "text" },
];

const OPERATOR_OPTIONS = [
  { value: "equal_to", label: "equals" },
  { value: "not_equal_to", label: "not equals" },
  { value: "contains", label: "contains" },
  { value: "does_not_contain", label: "does not contain" },
  { value: "is_present", label: "is present" },
  { value: "is_not_present", label: "is not present" },
  { value: "is_greater_than", label: "greater than" },
  { value: "is_less_than", label: "less than" },
  { value: "days_before", label: "days before" },
];

const QUERY_OPERATORS = ["AND", "OR"];

export function FilterBuilder({ onExecute, loading, connectionStatus }) {
  const [filters, setFilters] = useState([
    { attribute_key: "status", filter_operator: "equal_to", values: ["open"], query_operator: null },
  ]);
  const [page, setPage] = useState(1);

  const addFilter = () => {
    // Set query_operator on the current last filter
    const updated = filters.map((f, i) =>
      i === filters.length - 1 ? { ...f, query_operator: "AND" } : f
    );
    setFilters([
      ...updated,
      { attribute_key: "status", filter_operator: "equal_to", values: [""], query_operator: null },
    ]);
  };

  const removeFilter = (index) => {
    if (filters.length <= 1) return;
    const updated = filters.filter((_, i) => i !== index);
    // Ensure last filter has null query_operator
    updated[updated.length - 1] = { ...updated[updated.length - 1], query_operator: null };
    setFilters(updated);
  };

  const updateFilter = (index, field, value) => {
    setFilters((prev) =>
      prev.map((f, i) => (i === index ? { ...f, [field]: value } : f))
    );
  };

  const updateFilterValue = (index, value) => {
    const attr = ATTRIBUTE_OPTIONS.find((a) => a.value === filters[index].attribute_key);
    let parsed;
    if (attr?.type === "number") {
      parsed = [parseInt(value, 10) || 0];
    } else {
      parsed = value.split(",").map((v) => v.trim()).filter(Boolean);
    }
    updateFilter(index, "values", parsed);
  };

  const handleExecute = () => {
    const payload = filters.map((f) => ({
      attribute_key: f.attribute_key,
      filter_operator: f.filter_operator,
      values: f.values,
      query_operator: f.query_operator,
    }));
    onExecute("filter_conversations_advanced", {
      filters_json: JSON.stringify(payload),
      page,
    });
  };

  return (
    <div className="space-y-3" data-testid="filter-builder">
      <div className="flex items-center gap-2 mb-2">
        <Filter className="w-4 h-4 text-[#002FA7]" />
        <span className="font-mono text-xs font-semibold text-[#002FA7] uppercase tracking-wider">
          Conversation Filter Builder
        </span>
      </div>

      {filters.map((filter, index) => {
        const attr = ATTRIBUTE_OPTIONS.find((a) => a.value === filter.attribute_key);
        return (
          <div key={index}>
            <div className="flex flex-wrap gap-2 items-center bg-[#F5F5F5] border border-[#E5E5E5] p-2" data-testid={`filter-row-${index}`}>
              {/* Attribute */}
              <select
                value={filter.attribute_key}
                onChange={(e) => updateFilter(index, "attribute_key", e.target.value)}
                className="bg-white border border-[#E5E5E5] text-[#0A0A0A] font-mono text-xs px-2 py-1.5 min-w-[130px]"
                data-testid={`filter-attribute-${index}`}
              >
                {ATTRIBUTE_OPTIONS.map((a) => (
                  <option key={a.value} value={a.value}>{a.label}</option>
                ))}
              </select>

              {/* Operator */}
              <select
                value={filter.filter_operator}
                onChange={(e) => updateFilter(index, "filter_operator", e.target.value)}
                className="bg-white border border-[#E5E5E5] text-[#0A0A0A] font-mono text-xs px-2 py-1.5 min-w-[120px]"
                data-testid={`filter-operator-${index}`}
              >
                {OPERATOR_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>

              {/* Value */}
              {filter.filter_operator !== "is_present" && filter.filter_operator !== "is_not_present" && (
                attr?.type === "select" ? (
                  <select
                    value={filter.values[0] || ""}
                    onChange={(e) => updateFilter(index, "values", [e.target.value])}
                    className="bg-white border border-[#E5E5E5] text-[#0A0A0A] font-mono text-xs px-2 py-1.5 min-w-[100px]"
                    data-testid={`filter-value-${index}`}
                  >
                    {attr.options.map((o) => (
                      <option key={o} value={o}>{o}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    value={filter.values.join(",")}
                    onChange={(e) => updateFilterValue(index, e.target.value)}
                    placeholder={attr?.type === "number" ? "ID" : "value1,value2"}
                    className="bg-white border border-[#E5E5E5] text-[#0A0A0A] font-mono text-xs px-2 py-1.5 flex-1 min-w-[80px]"
                    data-testid={`filter-value-${index}`}
                  />
                )
              )}

              {/* Remove */}
              {filters.length > 1 && (
                <button
                  onClick={() => removeFilter(index)}
                  className="text-[#999] hover:text-[#FF2A2A] transition-colors p-1"
                  data-testid={`filter-remove-${index}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Query Operator */}
            {filter.query_operator && (
              <div className="flex justify-center py-1">
                <div className="flex gap-1">
                  {QUERY_OPERATORS.map((op) => (
                    <button
                      key={op}
                      onClick={() => updateFilter(index, "query_operator", op)}
                      className={`font-mono text-[10px] px-2 py-0.5 border transition-colors ${
                        filter.query_operator === op
                          ? "bg-[#002FA7] text-white border-[#002FA7]"
                          : "bg-white text-[#666] border-[#E5E5E5] hover:border-[#002FA7]"
                      }`}
                      data-testid={`filter-query-op-${index}-${op}`}
                    >
                      {op}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={addFilter}
          className="rounded-none text-xs border-[#E5E5E5] text-[#666] hover:text-[#0A0A0A]"
          data-testid="filter-add-button"
        >
          <Plus className="w-3 h-3 mr-1" />
          Add Condition
        </Button>
        <div className="flex items-center gap-1 ml-auto">
          <span className="font-mono text-[10px] text-[#666]">PAGE</span>
          <input
            type="number"
            value={page}
            onChange={(e) => setPage(parseInt(e.target.value, 10) || 1)}
            min={1}
            className="w-12 bg-white border border-[#E5E5E5] text-[#0A0A0A] font-mono text-xs px-1.5 py-1 text-center"
            data-testid="filter-page-input"
          />
        </div>
      </div>

      <Button
        onClick={handleExecute}
        disabled={loading || connectionStatus !== "connected"}
        className="w-full bg-[#002FA7] hover:bg-[#001B66] text-white font-mono text-xs uppercase tracking-wider rounded-none h-9 disabled:opacity-40"
        data-testid="filter-execute-button"
      >
        {loading ? (
          <>
            <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" />
            FILTERING...
          </>
        ) : (
          <>
            <Play className="w-3.5 h-3.5 mr-2" />
            EXECUTE FILTER
          </>
        )}
      </Button>

      {/* Preview payload */}
      <details className="mt-2">
        <summary className="font-mono text-[10px] text-[#999] cursor-pointer hover:text-[#666]">
          PREVIEW PAYLOAD
        </summary>
        <pre className="mt-1 p-2 bg-[#F5F5F5] border border-[#E5E5E5] font-mono text-[10px] text-[#666] overflow-x-auto">
          {JSON.stringify(
            filters.map((f) => ({
              attribute_key: f.attribute_key,
              filter_operator: f.filter_operator,
              values: f.values,
              query_operator: f.query_operator,
            })),
            null,
            2
          )}
        </pre>
      </details>
    </div>
  );
}
