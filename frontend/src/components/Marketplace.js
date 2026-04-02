import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { Search, Download, Loader as Loader2, ExternalLink, Check, GitBranch, Code as Code2, Database, Globe, MessageSquare, Shield, Cpu, FolderOpen, Zap } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const CATEGORY_ICONS = {
  developer: Code2,
  communication: MessageSquare,
  database: Database,
  search: Globe,
  utility: Zap,
  automation: Cpu,
  storage: FolderOpen,
  monitoring: Shield,
  community: GitBranch,
  other: Zap,
};

const CATEGORY_COLORS = {
  developer: "text-[#002FA7] bg-[#002FA7]/5 border-[#002FA7]/20",
  communication: "text-[#9333EA] bg-[#9333EA]/5 border-[#9333EA]/20",
  database: "text-[#D97706] bg-[#D97706]/5 border-[#D97706]/20",
  search: "text-[#059669] bg-[#059669]/5 border-[#059669]/20",
  utility: "text-[#666] bg-[#666]/5 border-[#666]/20",
  automation: "text-[#DC2626] bg-[#DC2626]/5 border-[#DC2626]/20",
  storage: "text-[#0891B2] bg-[#0891B2]/5 border-[#0891B2]/20",
  monitoring: "text-[#7C3AED] bg-[#7C3AED]/5 border-[#7C3AED]/20",
  community: "text-[#0A0A0A] bg-[#0A0A0A]/5 border-[#0A0A0A]/20",
  other: "text-[#999] bg-[#999]/5 border-[#999]/20",
};

export function Marketplace({ onInstall }) {
  const { axiosAuth } = useAuth();
  const [catalog, setCatalog] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [installing, setInstalling] = useState(null);

  const api = useCallback(() => axiosAuth(), [axiosAuth]);

  const fetchCatalog = useCallback(async () => {
    try {
      const resp = await api().get("/api/marketplace/catalog");
      setCatalog(resp.data.catalog || []);
      setCategories(resp.data.categories || []);
    } catch (e) {
      console.error("Failed to fetch marketplace", e);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => { fetchCatalog(); }, [fetchCatalog]);

  const filtered = catalog.filter((entry) => {
    const matchCat = !selectedCategory || entry.category === selectedCategory;
    const q = search.toLowerCase();
    const matchSearch = !q || entry.name.toLowerCase().includes(q) || entry.description.toLowerCase().includes(q);
    return matchCat && matchSearch;
  });

  const handleInstall = async (entry) => {
    setInstalling(entry.slug);
    try {
      // Add server
      await api().post("/api/servers/add", {
        github_url: entry.github_url,
        name: entry.slug,
        display_name: entry.name,
        description: entry.description,
        runtime: entry.runtime,
        command: entry.command,
        args: entry.args,
        npm_package: entry.npm_package || "",
        pip_package: entry.pip_package || "",
        credentials_schema: entry.credentials_schema || [],
        features: entry.features || [],
      });
      await fetchCatalog();
      if (onInstall) onInstall(entry);
    } catch (e) {
      const detail = e.response?.data?.detail || "";
      if (detail.includes("already exists")) {
        // Already installed — just refresh
        await fetchCatalog();
      } else {
        console.error("Install failed:", detail);
      }
    } finally {
      setInstalling(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-6 h-6 animate-spin text-[#002FA7]" />
      </div>
    );
  }

  return (
    <div data-testid="marketplace">
      {/* Search + Filter */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#999]" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search MCP servers..."
            className="pl-9 rounded-none border-[#E5E5E5] font-mono text-sm"
            data-testid="marketplace-search"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          <button
            onClick={() => setSelectedCategory("")}
            className={`px-2.5 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors ${
              !selectedCategory ? "bg-[#0A0A0A] text-white border-[#0A0A0A]" : "bg-white text-[#666] border-[#E5E5E5] hover:border-[#0A0A0A]"
            }`}
            data-testid="marketplace-filter-all"
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat === selectedCategory ? "" : cat)}
              className={`px-2.5 py-1 text-[10px] font-mono uppercase tracking-wider border transition-colors ${
                cat === selectedCategory ? "bg-[#0A0A0A] text-white border-[#0A0A0A]" : "bg-white text-[#666] border-[#E5E5E5] hover:border-[#0A0A0A]"
              }`}
              data-testid={`marketplace-filter-${cat}`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((entry) => {
          const Icon = CATEGORY_ICONS[entry.category] || Zap;
          const colorCls = CATEGORY_COLORS[entry.category] || CATEGORY_COLORS.other;

          return (
            <div
              key={entry.slug}
              className="bg-white border border-[#E5E5E5] hover:border-[#002FA7] transition-all flex flex-col"
              data-testid={`marketplace-card-${entry.slug}`}
            >
              <div className="p-4 flex-1">
                <div className="flex items-start gap-3 mb-3">
                  <div className={`w-10 h-10 flex items-center justify-center border flex-shrink-0 ${colorCls}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-bold text-[#0A0A0A] text-sm">{entry.name}</h3>
                      <Badge variant="outline" className={`text-[9px] font-mono px-1 py-0 ${colorCls}`}>
                        {entry.category}
                      </Badge>
                      {entry.source === "community" && (
                        <Badge variant="outline" className="text-[9px] font-mono px-1 py-0 text-[#666] border-[#CCC]">
                          community
                        </Badge>
                      )}
                    </div>
                    <Badge variant="outline" className="text-[9px] font-mono px-1 py-0 mt-1 text-[#999] border-[#DDD]">
                      {entry.runtime}
                    </Badge>
                  </div>
                </div>
                <p className="text-xs text-[#666] line-clamp-2 mb-3">{entry.description}</p>
                {entry.credentials_schema?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {entry.credentials_schema.map((cs) => (
                      <span key={cs.key} className="text-[9px] font-mono text-[#999] bg-[#F5F5F5] px-1.5 py-0.5">
                        {cs.key}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="px-4 py-3 border-t border-[#E5E5E5] flex items-center justify-between">
                {entry.github_url && (
                  <a
                    href={entry.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] font-mono text-[#002FA7] hover:underline flex items-center gap-1"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Source
                  </a>
                )}
                {entry.installed ? (
                  <Badge className="bg-[#00E559]/10 text-[#00A040] border border-[#00E559]/30 text-[10px] font-mono px-2 py-0.5">
                    <Check className="w-3 h-3 mr-1" />
                    Installed
                  </Badge>
                ) : (
                  <Button
                    size="sm"
                    className="bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none text-[10px] font-mono h-7 px-3"
                    onClick={() => handleInstall(entry)}
                    disabled={installing === entry.slug}
                    data-testid={`install-${entry.slug}`}
                  >
                    {installing === entry.slug ? (
                      <Loader2 className="w-3 h-3 animate-spin mr-1" />
                    ) : (
                      <Download className="w-3 h-3 mr-1" />
                    )}
                    Install
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-[#999]">
          <Globe className="w-8 h-8 mx-auto mb-2 text-[#DDD]" />
          <p className="font-mono text-sm">No servers match your search</p>
        </div>
      )}
    </div>
  );
}
