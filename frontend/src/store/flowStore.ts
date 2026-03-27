import { create } from "zustand";

export interface Flow {
  id: string;
  symbol: string;
  strike: number;
  expiry: string;
  put_call: string;
  direction: "BULLISH" | "BEARISH" | "NEUTRAL";
  premium: number;
  score: number;
  is_sweep: boolean;
  is_dark_pool?: boolean;
  side?: string;
  ai_note?: string;
  timestamp: string;
  volume?: number;
  open_interest?: number;
}

export interface FlowFilters {
  symbols: string[];
  min_premium: number;
  direction: "ALL" | "BULLISH" | "BEARISH";
  min_score: number;
}

interface FlowState {
  flows: Flow[];
  filters: FlowFilters;
  connected: boolean;
  addFlow: (flow: Flow) => void;
  setFlows: (flows: Flow[]) => void;
  updateFilters: (filters: Partial<FlowFilters>) => void;
  setConnected: (connected: boolean) => void;
  clearFlows: () => void;
}

const MAX_FLOWS = 500;

export const useFlowStore = create<FlowState>((set) => ({
  flows: [],
  filters: {
    symbols: [],
    min_premium: 0,
    direction: "ALL",
    min_score: 0,
  },
  connected: false,

  addFlow: (flow) =>
    set((state) => ({
      flows: [flow, ...state.flows].slice(0, MAX_FLOWS),
    })),

  setFlows: (flows) => set({ flows: flows.slice(0, MAX_FLOWS) }),

  updateFilters: (partial) =>
    set((state) => ({
      filters: { ...state.filters, ...partial },
    })),

  setConnected: (connected) => set({ connected }),

  clearFlows: () => set({ flows: [] }),
}));
