"use client";

import { useEffect, useRef, useCallback } from "react";
import { useFlowStore, type Flow, type FlowFilters } from "@/store/flowStore";
import { wsUrl, apiFetch } from "@/lib/api";

const MAX_RECONNECT_DELAY = 30000;
const BASE_DELAY = 1000;

export function useFlowStream(filters?: Partial<FlowFilters>) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attempt = useRef(0);
  const initialLoaded = useRef(false);
  const { addFlow, setFlows, setConnected, connected, flows } = useFlowStore();

  useEffect(() => {
    if (initialLoaded.current) return;
    initialLoaded.current = true;
    apiFetch<Flow[]>("/api/v1/flows?limit=200")
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setFlows(data);
        }
      })
      .catch(() => {});
  }, [setFlows]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(wsUrl("/ws/flows"));
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      attempt.current = 0;
      if (filters) {
        ws.send(JSON.stringify(filters));
      }
    };

    ws.onmessage = (event) => {
      try {
        const flow: Flow = JSON.parse(event.data);
        addFlow(flow);
      } catch {
        /* ignore malformed messages */
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      const delay = Math.min(
        BASE_DELAY * Math.pow(2, attempt.current),
        MAX_RECONNECT_DELAY
      );
      attempt.current += 1;
      reconnectTimer.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [filters, addFlow, setConnected]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current ?? undefined);
      wsRef.current?.close();
    };
  }, [connect]);

  useEffect(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN && filters) {
      wsRef.current.send(JSON.stringify(filters));
    }
  }, [filters]);

  return { connected, flows, error: null };
}
