import { useState } from "react";
import {
  Search,
  Users,
  MessageSquare,
  Mail,
  Inbox,
  UserCheck,
  Tag,
  MessageCircle,
  Globe,
  BarChart3,
  Webhook,
  Layers,
  FileText,
  ChevronRight,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

const CATEGORY_ICONS = {
  all: Layers,
  account: Globe,
  agents: UserCheck,
  contacts: Users,
  conversations: MessageSquare,
  messages: Mail,
  inboxes: Inbox,
  teams: Users,
  labels: Tag,
  canned_responses: MessageCircle,
  custom_attributes: FileText,
  webhooks: Webhook,
  reports: BarChart3,
};

const CATEGORY_LABELS = {
  all: "All Tools",
  account: "Account",
  agents: "Agents",
  contacts: "Contacts",
  conversations: "Conversations",
  messages: "Messages",
  inboxes: "Inboxes",
  teams: "Teams",
  labels: "Labels",
  canned_responses: "Canned Responses",
  custom_attributes: "Custom Attrs",
  webhooks: "Webhooks",
  reports: "Reports",
};

const METHOD_COLORS = {
  get: "bg-[#00E559]/10 text-[#00A040] border-[#00E559]/30",
  list: "bg-[#00E559]/10 text-[#00A040] border-[#00E559]/30",
  create: "bg-[#002FA7]/10 text-[#002FA7] border-[#002FA7]/30",
  add: "bg-[#002FA7]/10 text-[#002FA7] border-[#002FA7]/30",
  update: "bg-[#FFCC00]/10 text-[#997A00] border-[#FFCC00]/30",
  delete: "bg-[#FF2A2A]/10 text-[#FF2A2A] border-[#FF2A2A]/30",
  remove: "bg-[#FF2A2A]/10 text-[#FF2A2A] border-[#FF2A2A]/30",
  toggle: "bg-[#c084fc]/10 text-[#8B5CF6] border-[#c084fc]/30",
  assign: "bg-[#c084fc]/10 text-[#8B5CF6] border-[#c084fc]/30",
  search: "bg-[#38bdf8]/10 text-[#0284C7] border-[#38bdf8]/30",
  filter: "bg-[#38bdf8]/10 text-[#0284C7] border-[#38bdf8]/30",
};

function getMethodBadge(name) {
  const lower = name.toLowerCase();
  for (const [key, cls] of Object.entries(METHOD_COLORS)) {
    if (lower.startsWith(key)) return { label: key.toUpperCase(), cls };
  }
  return { label: "RUN", cls: "bg-[#F5F5F5] text-[#666] border-[#E5E5E5]" };
}

export function ToolExplorer({
  tools,
  categories,
  selectedCategory,
  onCategoryChange,
  searchQuery,
  onSearchChange,
  selectedTool,
  onSelectTool,
}) {
  const [hoveredTool, setHoveredTool] = useState(null);

  return (
    <div
      className="flex-1 flex flex-col overflow-hidden bg-white border-r border-[#E5E5E5]"
      data-testid="tool-explorer"
    >
      {/* Header */}
      <div className="p-4 border-b border-[#E5E5E5]">
        <h2 className="font-heading text-xl font-bold tracking-tight text-[#0A0A0A] mb-3" data-testid="tool-explorer-title">
          Tool Explorer
        </h2>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#999]" />
          <Input
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search tools..."
            className="pl-10 font-mono text-sm rounded-none border-[#E5E5E5] focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7]"
            data-testid="tool-search-input"
          />
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex overflow-x-auto border-b border-[#E5E5E5] bg-[#FAFAFA]">
        {categories.map((cat) => {
          const Icon = CATEGORY_ICONS[cat] || Layers;
          const isActive = selectedCategory === cat;
          const count = cat === "all" ? tools.length : tools.filter((t) => t.category === cat).length;
          return (
            <button
              key={cat}
              onClick={() => onCategoryChange(cat)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors duration-150 ${
                isActive
                  ? "border-[#002FA7] text-[#002FA7] bg-white"
                  : "border-transparent text-[#666] hover:text-[#0A0A0A] hover:bg-[#F0F0F0]"
              }`}
              data-testid={`category-filter-${cat}`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{CATEGORY_LABELS[cat] || cat}</span>
              {cat !== "all" && (
                <span className="text-[10px] font-mono opacity-60">{count}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tool List */}
      <ScrollArea className="flex-1">
        <div className="divide-y divide-[#E5E5E5]">
          {tools.length === 0 ? (
            <div className="p-8 text-center grid-bg min-h-[200px] flex items-center justify-center">
              <div>
                <Search className="w-8 h-8 text-[#ccc] mx-auto mb-2" />
                <p className="text-sm text-[#999]">No tools found</p>
              </div>
            </div>
          ) : (
            tools.map((tool) => {
              const method = getMethodBadge(tool.name);
              const isSelected = selectedTool?.name === tool.name;
              const isHovered = hoveredTool === tool.name;
              return (
                <button
                  key={tool.name}
                  onClick={() => onSelectTool(tool)}
                  onMouseEnter={() => setHoveredTool(tool.name)}
                  onMouseLeave={() => setHoveredTool(null)}
                  className={`w-full text-left px-4 py-3 flex items-start gap-3 transition-colors duration-150 ${
                    isSelected
                      ? "bg-[#002FA7]/5 border-l-2 border-l-[#002FA7]"
                      : isHovered
                      ? "bg-[#F5F5F5]"
                      : ""
                  }`}
                  data-testid={`tool-item-${tool.name}`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        variant="outline"
                        className={`text-[10px] font-mono px-1.5 py-0 border rounded-none ${method.cls}`}
                      >
                        {method.label}
                      </Badge>
                      <span className="font-mono text-sm font-medium text-[#0A0A0A] truncate">
                        {tool.name}
                      </span>
                    </div>
                    <p className="text-xs text-[#666] line-clamp-2 leading-relaxed">
                      {tool.description}
                    </p>
                    {tool.parameters.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {tool.parameters.slice(0, 4).map((p) => (
                          <span
                            key={p.name}
                            className={`text-[10px] font-mono px-1.5 py-0.5 border ${
                              p.required
                                ? "text-[#002FA7] border-[#002FA7]/20 bg-[#002FA7]/5"
                                : "text-[#999] border-[#E5E5E5] bg-[#FAFAFA]"
                            }`}
                          >
                            {p.name}
                          </span>
                        ))}
                        {tool.parameters.length > 4 && (
                          <span className="text-[10px] font-mono text-[#999]">
                            +{tool.parameters.length - 4}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <ChevronRight
                    className={`w-4 h-4 flex-shrink-0 mt-1 transition-colors ${
                      isSelected ? "text-[#002FA7]" : "text-[#ccc]"
                    }`}
                  />
                </button>
              );
            })
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-[#E5E5E5] bg-[#FAFAFA]">
        <span className="text-[10px] font-mono text-[#999] uppercase tracking-wider">
          {tools.length} TOOLS AVAILABLE
        </span>
      </div>
    </div>
  );
}
