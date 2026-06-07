"use client";
import { type JournalEntry } from "@/lib/api";

interface Props {
  entries: JournalEntry[];
  filterSymbol: string;
  onFilterChange: (s: string) => void;
}

export default function JournalList({ entries, filterSymbol, onFilterChange }: Props) {
  if (entries.length === 0) {
    return (
      <div className="text-center text-gray-400 py-12">
        {filterSymbol ? `「${filterSymbol}」暂无交易记录` : "还没有交易记录"}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {filterSymbol && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">只看：</span>
          <span className="text-sm bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">{filterSymbol}</span>
          <button
            onClick={() => onFilterChange("")}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            清除筛选
          </button>
        </div>
      )}

      {entries.map((entry) => {
        const isBuy = entry.action === "buy";
        const pnl = entry.pnl ? parseFloat(entry.pnl) : null;

        return (
          <div
            key={entry.id}
            className="bg-white rounded-xl border border-gray-100 px-5 py-4 flex flex-col sm:flex-row sm:items-start gap-3"
          >
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <span
                className={`shrink-0 text-xs font-bold px-2.5 py-1 rounded-full ${
                  isBuy
                    ? "bg-red-50 text-[var(--color-gain)]"
                    : "bg-green-50 text-[var(--color-loss)]"
                }`}
              >
                {isBuy ? "买" : "卖"}
              </span>

              <div className="min-w-0">
                <div className="flex items-baseline gap-2 flex-wrap">
                  <span className="font-medium text-gray-800">{entry.symbol}</span>
                  <span className="text-sm text-gray-500">
                    {parseFloat(entry.shares).toLocaleString()} 股 · ¥{parseFloat(entry.price).toFixed(3)}
                  </span>
                  {pnl !== null && (
                    <span
                      className={`text-sm font-medium ${pnl >= 0 ? "text-[var(--color-gain)]" : "text-[var(--color-loss)]"}`}
                    >
                      {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)} 元
                    </span>
                  )}
                </div>
                {entry.reason && (
                  <p className="text-sm text-gray-500 mt-0.5 truncate">{entry.reason}</p>
                )}
              </div>
            </div>

            <div className="text-xs text-gray-400 shrink-0 text-right">
              <div>{entry.trade_date}</div>
              {entry.avg_cost_at_time && (
                <div>均价 ¥{parseFloat(entry.avg_cost_at_time).toFixed(3)}</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
