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
  motivation_type?: string;
  ai_audit?: string;
}

export interface RefreshResult {
  updated: number;
  skipped: number;
  errors: string[];
}

export interface ParsedTrade {
  row_index: number;
  trade_date: string | null;
  symbol: string | null;
  name: string | null;
  asset_type: string;
  action: Action | null;
  shares: string | null;
  price: string | null;
  fee: string;
  external_id: string | null;
  status: "ok" | "skip" | "error";
  note: string | null;
}

export interface PreviewResult {
  rows: ParsedTrade[];
  parsable_count: number;
  skip_count: number;
  error_count: number;
  dup_count: number;
}

export interface CommitResult {
  imported: number;
  skipped_dup: number;
  failed: { row: number; reason: string }[];
  committed: boolean;
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
    delete: (id: number) =>
      fetch(`${BASE}/journal/${id}`, { method: "DELETE" }),
  },
  prices: {
    refresh: () => request<RefreshResult>("/prices/refresh", { method: "POST" }),
  },
  import: {
    preview: async (file: File, broker: string): Promise<PreviewResult> => {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("broker", broker);
      // 走裸 fetch：FormData 需浏览器自动设置 multipart boundary，不能套 JSON 头
      const res = await fetch(`${BASE}/import/preview`, { method: "POST", body: fd });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }
      return res.json();
    },
    commit: (rows: ParsedTrade[]) =>
      request<CommitResult>("/import/commit", {
        method: "POST",
        body: JSON.stringify({ rows }),
      }),
  },
};
