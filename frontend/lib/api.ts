const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export type AssetType = "stock" | "etf" | "fund";
export type Action = "buy" | "sell";

export interface Position {
  id: number;
  symbol: string;
  name: string;
  asset_type: AssetType;
  shares: string;
  avg_cost: string;
  current_price: string | null;
  price_date: string | null;
  is_stale: boolean;
}

export interface JournalEntry {
  id: number;
  symbol: string;
  action: Action;
  shares: string;
  price: string;
  reason: string | null;
  pnl: string | null;
  avg_cost_at_time: string | null;
  trade_date: string;
  created_at: string;
}

export interface RefreshResult {
  updated: number;
  skipped: number;
  errors: string[];
}

export const api = {
  positions: {
    list: () => request<Position[]>("/positions"),
    create: (body: {
      symbol: string;
      name: string;
      asset_type: AssetType;
      shares: number;
      avg_cost: number;
    }) => request<Position>("/positions", { method: "POST", body: JSON.stringify(body) }),
    delete: (symbol: string) =>
      fetch(`${BASE}/positions/${symbol}`, { method: "DELETE" }),
  },
  journal: {
    list: (symbol?: string) =>
      request<JournalEntry[]>(`/journal${symbol ? `?symbol=${symbol}` : ""}`),
    create: (body: {
      symbol: string;
      action: Action;
      shares: number;
      price: number;
      reason?: string;
      trade_date: string;
    }) => request<JournalEntry>("/journal", { method: "POST", body: JSON.stringify(body) }),
  },
  prices: {
    refresh: () => request<RefreshResult>("/prices/refresh", { method: "POST" }),
  },
};
