import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { Key, Plus, Trash2, Copy, Check, Loader2, Shield, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export function ApiKeyManager({ appName }) {
  const { axiosAuth } = useAuth();
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newLabel, setNewLabel] = useState("");
  const [newKey, setNewKey] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  const api = useCallback(() => axiosAuth(), [axiosAuth]);

  const fetchKeys = useCallback(async () => {
    try {
      const resp = await api().get(`/api/apps/${appName}/keys`);
      setKeys(resp.data.keys || []);
    } catch (e) {
      console.error("Failed to fetch keys", e);
    } finally {
      setLoading(false);
    }
  }, [api, appName]);

  useEffect(() => { fetchKeys(); }, [fetchKeys]);

  const handleCreate = async () => {
    if (!newLabel.trim()) return;
    setCreating(true);
    try {
      const resp = await api().post(`/api/apps/${appName}/keys`, { label: newLabel.trim() });
      setNewKey(resp.data);
      setNewLabel("");
      fetchKeys();
    } catch (e) {
      console.error("Failed to create key", e);
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (keyId) => {
    if (!window.confirm("Revoke this API key? This cannot be undone.")) return;
    try {
      await api().delete(`/api/apps/${appName}/keys/${keyId}`);
      fetchKeys();
    } catch (e) {
      console.error("Failed to revoke key", e);
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6" data-testid="api-key-manager">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-[#0A0A0A] flex items-center gap-2">
          <Shield className="w-5 h-5 text-[#002FA7]" />
          API Keys
        </h2>
        <p className="text-sm text-[#666] mt-1">
          Manage API keys for external access to the <span className="font-mono font-semibold">{appName}</span> MCP server.
          Use these keys in the <code className="bg-[#F0F0F0] px-1.5 py-0.5 text-xs font-mono">Authorization: Bearer</code> header
          or <code className="bg-[#F0F0F0] px-1.5 py-0.5 text-xs font-mono">X-API-Key</code> header.
        </p>
      </div>

      {/* Create new key */}
      <div className="bg-[#F9F9F9] border border-[#E5E5E5] p-4 space-y-3">
        <h3 className="text-sm font-bold text-[#0A0A0A] uppercase tracking-wider">Create New Key</h3>
        <div className="flex gap-2">
          <Input
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            placeholder="Key label (e.g. n8n-production)"
            className="flex-1 rounded-none border-[#E5E5E5] font-mono text-sm"
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            data-testid="api-key-label-input"
          />
          <Button
            onClick={handleCreate}
            disabled={creating || !newLabel.trim()}
            className="bg-[#002FA7] hover:bg-[#001B66] text-white rounded-none font-mono text-xs px-4"
            data-testid="create-api-key-button"
          >
            {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4 mr-1" />}
            Create
          </Button>
        </div>
      </div>

      {/* Newly created key (show once) */}
      {newKey && (
        <div className="bg-[#00E559]/5 border border-[#00E559]/30 p-4 space-y-2" data-testid="new-key-display">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#00E559]">Key Created — Copy Now!</h3>
            <button onClick={() => setNewKey(null)} className="text-xs text-[#666] hover:text-[#0A0A0A]">Dismiss</button>
          </div>
          <p className="text-xs text-[#666]">This key will only be shown once. Store it securely.</p>
          <div className="flex items-center gap-2 bg-[#0A0A0A] px-3 py-2">
            <code className="flex-1 font-mono text-sm text-[#00E559] break-all" data-testid="new-key-value">{newKey.key}</code>
            <button
              onClick={() => copyToClipboard(newKey.key, "new")}
              className="text-[#666] hover:text-[#00E559] flex-shrink-0"
              data-testid="copy-new-key-button"
            >
              {copiedId === "new" ? <Check className="w-4 h-4 text-[#00E559]" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <p className="text-xs font-mono text-[#888]">Label: {newKey.label}</p>
        </div>
      )}

      {/* Keys list */}
      <div className="space-y-2">
        <h3 className="text-sm font-bold text-[#0A0A0A] uppercase tracking-wider">
          Active Keys ({keys.filter((k) => k.is_active).length})
        </h3>
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-[#002FA7]" />
          </div>
        ) : keys.length === 0 ? (
          <div className="text-center py-8 text-[#999] border border-dashed border-[#E5E5E5]">
            <Key className="w-8 h-8 mx-auto mb-2 text-[#DDD]" />
            <p className="text-sm">No API keys yet</p>
          </div>
        ) : (
          <div className="divide-y divide-[#E5E5E5] border border-[#E5E5E5]">
            {keys.map((k) => (
              <div
                key={k.key_id}
                className={`flex items-center gap-3 px-4 py-3 ${!k.is_active ? "opacity-50 bg-[#F9F9F9]" : "bg-white"}`}
                data-testid={`api-key-row-${k.key_id}`}
              >
                <Key className={`w-4 h-4 flex-shrink-0 ${k.is_active ? "text-[#002FA7]" : "text-[#CCC]"}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold text-[#0A0A0A] truncate">{k.label}</span>
                    <Badge
                      variant="outline"
                      className={`text-[10px] font-mono uppercase px-1.5 py-0 ${
                        k.is_active
                          ? "text-[#00E559] border-[#00E559]/30"
                          : "text-[#FF2A2A] border-[#FF2A2A]/30"
                      }`}
                    >
                      {k.is_active ? "Active" : "Revoked"}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="font-mono text-xs text-[#888]">{k.key_preview}</span>
                    <span className="text-[10px] text-[#BBB]">{new Date(k.created_at).toLocaleDateString()}</span>
                    {k.revoked_at && (
                      <span className="text-[10px] text-[#FF2A2A]">Revoked {new Date(k.revoked_at).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
                {k.is_active && (
                  <button
                    onClick={() => handleRevoke(k.key_id)}
                    className="text-[#CCC] hover:text-[#FF2A2A] transition-colors flex-shrink-0"
                    title="Revoke key"
                    data-testid={`revoke-key-${k.key_id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Usage hint */}
      <div className="bg-[#F0F0FF] border border-[#002FA7]/10 p-4 text-xs text-[#666] space-y-2">
        <h4 className="font-bold text-[#002FA7] uppercase tracking-wider text-[11px]">Usage</h4>
        <p>Use your API key to authenticate requests to the MCP server endpoints:</p>
        <pre className="bg-[#0A0A0A] text-[#E5E5E5] p-3 font-mono text-[11px] whitespace-pre-wrap">
{`# Header auth
curl -H "X-API-Key: mcp_your_key_here" \\
  ${process.env.REACT_APP_BACKEND_URL}/api/${appName}/mcp/sse

# Bearer auth
curl -H "Authorization: Bearer mcp_your_key_here" \\
  ${process.env.REACT_APP_BACKEND_URL}/api/${appName}/tools/execute`}
        </pre>
      </div>
    </div>
  );
}
