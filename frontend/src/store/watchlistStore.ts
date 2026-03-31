"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { apiFetch } from "@/lib/api";

export const DEFAULT_SYMBOLS = [
  "NVDA", "AAPL", "TSLA", "SPY", "QQQ",
  "AMZN", "MSFT", "META", "GOOGL", "AMD",
];

interface WatchlistResponse {
  symbols: string[];
}

interface WatchlistState {
  symbols: string[];
  synced: boolean;
  addSymbol: (symbol: string) => void;
  removeSymbol: (symbol: string) => void;
  resetToDefault: () => void;
  syncFromServer: () => void;
}

export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set, get) => ({
      symbols: DEFAULT_SYMBOLS,
      synced: false,

      addSymbol: (symbol) => {
        const sym = symbol.trim().toUpperCase();
        if (!sym) return;
        const state = get();
        if (state.symbols.includes(sym) || state.symbols.length >= 30) return;
        set({ symbols: [...state.symbols, sym] });
        apiFetch<WatchlistResponse>("/api/v1/watchlist", {
          method: "POST",
          body: JSON.stringify({ symbol: sym }),
        }).catch(() => {});
      },

      removeSymbol: (symbol) => {
        const sym = symbol.trim().toUpperCase();
        set((state) => ({ symbols: state.symbols.filter((s) => s !== sym) }));
        apiFetch<WatchlistResponse>(`/api/v1/watchlist/${sym}`, {
          method: "DELETE",
        }).catch(() => {});
      },

      resetToDefault: () => {
        set({ symbols: DEFAULT_SYMBOLS });
        apiFetch<WatchlistResponse>("/api/v1/watchlist", { method: "GET" })
          .then(async (data) => {
            const current = new Set(data.symbols);
            const defaults = new Set(DEFAULT_SYMBOLS);
            for (const sym of current) {
              if (!defaults.has(sym)) {
                await apiFetch(`/api/v1/watchlist/${sym}`, { method: "DELETE" }).catch(() => {});
              }
            }
            for (const sym of DEFAULT_SYMBOLS) {
              if (!current.has(sym)) {
                await apiFetch("/api/v1/watchlist", {
                  method: "POST",
                  body: JSON.stringify({ symbol: sym }),
                }).catch(() => {});
              }
            }
          })
          .catch(() => {});
      },

      syncFromServer: () => {
        apiFetch<WatchlistResponse>("/api/v1/watchlist")
          .then((data) => {
            if (data.symbols.length > 0) {
              set({ symbols: data.symbols, synced: true });
            }
          })
          .catch(() => {});
      },
    }),
    {
      name: "optionflow-watchlist",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ symbols: state.symbols }),
    }
  )
);
