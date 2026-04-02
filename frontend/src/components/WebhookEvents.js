import { useState, useEffect, useRef } from "react";
import {
  Radio,
  Trash2,
  Pause,
  Play,
  Bell,
  BellOff,
  ChevronDown,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const EVENT_COLORS = {
  message_created: "bg-[#002FA7]/10 text-[#002FA7] border-[#002FA7]/30",
  message_updated: "bg-[#FFCC00]/10 text-[#997A00] border-[#FFCC00]/30",
  conversation_created: "bg-[#00E559]/10 text-[#00A040] border-[#00E559]/30",
  conversation_status_changed: "bg-[#c084fc]/10 text-[#8B5CF6] border-[#c084fc]/30",
  conversation_updated: "bg-[#38bdf8]/10 text-[#0284C7] border-[#38bdf8]/30",
  contact_created: "bg-[#f97316]/10 text-[#EA580C] border-[#f97316]/30",
  contact_updated: "bg-[#f97316]/10 text-[#EA580C] border-[#f97316]/30",
};

export function WebhookEvents({ serverName = "chatwoot" }) {
  const [events, setEvents] = useState([]);
  const [paused, setPaused] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const [connected, setConnected] = useState(false);
  const evtSourceRef = useRef(null);
  const pausedRef = useRef(false);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  // Load history on mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const resp = await axios.get(`${BACKEND_URL}/api/servers/${serverName}/webhooks/events/history?limit=30`, {
          headers: { Authorization: `Bearer ${localStorage.getItem("mcp_token") || ""}` },
        });
        setEvents(resp.data.events || []);
      } catch (e) {
        console.error("Failed to load webhook history", e);
      }
    };
    loadHistory();
  }, [serverName]);

  // SSE connection
  useEffect(() => {
    const token = localStorage.getItem("mcp_token") || "";
    const url = `${BACKEND_URL}/api/servers/${serverName}/webhooks/events${token ? `?api_key=${token}` : ""}`;
    const evtSource = new EventSource(url);
    evtSourceRef.current = evtSource;

    evtSource.onopen = () => setConnected(true);
    evtSource.onerror = () => setConnected(false);
    evtSource.onmessage = (e) => {
      if (pausedRef.current) return;
      try {
        const event = JSON.parse(e.data);
        setEvents((prev) => [event, ...prev].slice(0, 100));
      } catch (err) {
        console.error("Failed to parse webhook event", err);
      }
    };

    return () => {
      evtSource.close();
    };
  }, [serverName]);

  const clearEvents = () => {
    setEvents([]);
    setExpanded(null);
  };

  const toggleEvent = (idx) => {
    setExpanded((prev) => (prev === idx ? null : idx));
  };

  const formatTime = (ts) => {
    if (!ts) return "";
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  return (
    <div className="flex flex-col h-full" data-testid="webhook-events-panel">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#E5E5E5]">
        <div className="flex items-center gap-2">
          <Radio className="w-3.5 h-3.5 text-[#002FA7]" />
          <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[#0A0A0A]">
            Webhook Events
          </span>
          <Badge
            variant="outline"
            className={`text-[10px] font-mono px-1.5 py-0 border rounded-none ${
              connected
                ? "bg-[#00E559]/10 text-[#00E559] border-[#00E559]/30"
                : "bg-[#999]/10 text-[#666] border-[#999]/30"
            }`}
            data-testid="webhook-stream-status"
          >
            {connected ? "LIVE" : "OFFLINE"}
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPaused(!paused)}
            className="text-[#666] hover:text-[#0A0A0A] p-1 transition-colors"
            title={paused ? "Resume" : "Pause"}
            data-testid="webhook-pause-button"
          >
            {paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={clearEvents}
            className="text-[#666] hover:text-[#FF2A2A] p-1 transition-colors"
            title="Clear events"
            data-testid="webhook-clear-button"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-y-auto">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center px-4">
            <BellOff className="w-8 h-8 text-[#ccc] mb-2" />
            <p className="font-mono text-xs text-[#999]">NO EVENTS YET</p>
            <p className="text-[10px] text-[#ccc] mt-1 max-w-[200px]">
              Configure a webhook in Chatwoot pointing to your server's webhook receiver endpoint
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[#E5E5E5]">
            {events.map((evt, idx) => {
              const eventType = evt.event || "unknown";
              const colorCls = EVENT_COLORS[eventType] || "bg-[#F5F5F5] text-[#666] border-[#E5E5E5]";
              const isExpanded = expanded === idx;
              return (
                <button
                  key={idx}
                  onClick={() => toggleEvent(idx)}
                  className="w-full text-left px-3 py-2 hover:bg-[#F5F5F5] transition-colors"
                  data-testid={`webhook-event-${idx}`}
                >
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={`text-[9px] font-mono px-1 py-0 border rounded-none ${colorCls}`}>
                      {eventType}
                    </Badge>
                    <span className="font-mono text-[10px] text-[#999] ml-auto flex-shrink-0">
                      {formatTime(evt.received_at)}
                    </span>
                    <ChevronDown className={`w-3 h-3 text-[#ccc] transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                  </div>
                  {isExpanded && (
                    <pre className="mt-2 p-2 bg-[#FAFAFA] border border-[#E5E5E5] font-mono text-[10px] text-[#666] overflow-x-auto max-h-[200px] whitespace-pre-wrap break-all">
                      {JSON.stringify(evt.data, null, 2)}
                    </pre>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-[#E5E5E5] bg-[#FAFAFA]">
        <span className="font-mono text-[10px] text-[#999]">
          {events.length} events {paused && "| PAUSED"}
        </span>
      </div>
    </div>
  );
}
