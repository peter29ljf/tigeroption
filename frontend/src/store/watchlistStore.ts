"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export const DEFAULT_SYMBOLS = [
  "NVDA", "AAPL", "TSLA", "SPY", "QQQ",
  "AMZN", "MSFT", "META", "GOOGL", "AMD",
];

interface WatchlistState {
  symbols: string[];
  addSymbol: (symbol: string) => void;
  removeSymbol: (symbol: string) => void;
  resetToDefault: () => void;
}

export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set) => ({
      symbols: DEFAULT_SYMBOLS,

      addSymbol: (symbol) => {
        const sym = symbol.trim().toUpperCase();
        if (!sym) return;
        set((state) => {
          if (state.symbols.includes(sym) || state.symbols.length >= 30) return state;
          return { symbols: [...state.symbols, sym] };
        });
      },

      removeSymbol: (symbol) => {
        const sym = symbol.trim().toUpperCase();
        set((state) => ({ symbols: state.symbols.filter((s) => s !== sym) }));
      },

      resetToDefault: () => set({ symbols: DEFAULT_SYMBOLS }),
    }),
    {
      name: "optionflow-watchlist",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ symbols: state.symbols }),
    }
  )
);
