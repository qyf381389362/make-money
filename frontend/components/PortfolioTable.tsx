"use client";
import { useState } from "react";
import { type Position } from "@/lib/api";
import RecordTradeModal from "./RecordTradeModal";

interface Props {
  positions: Position[];
  onRefresh: () => void;
}

function pnlColor(pct: number) {
  if (pct > 0) return "text-[var(--color-gain)]";
  if (pct < 0) return "text-[var(--color-loss)]";
  return "text-[var(--color-neutral)]";
}

function RowSkeleton() {
  return (
    <tr>
      {[...Array(8)].map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-gray-200 rounded animate-pulse w-16" />
        </td>
      ))}
    </tr>
  );
}

export default function PortfolioTable({ positions, onRefresh }: Props) {
  const [tradeTarget, setTradeTarget] = useState<Position | null>(null);

  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-gray-500 text-xs uppercase tracking-wide">
              <th className="px-4 py-3 text-left">代码 / 名称</th>
              <th className="px-4 py-3 text-right">持仓量</th>
              <th className="px-4 py-3 text-right">均价</th>
              <th className="px-4 py-3 text-right">现价</th>
              <th className="px-4 py-3 text-right">盈亏金额</th>
              <th className="px-4 py-3 text-right">盈亏%</th>
              <th className="px-4 py-3 text-right">总成本</th>
              <th className="px-4 py-3 text-right">市值</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {positions.map((pos) => {
              const shares = parseFloat(pos.shares);
              const avgCost = parseFloat(pos.avg_cost);
              const currentPrice = pos.current_price ? parseFloat(pos.current_price) : null;
              const cost = shares * avgCost;
              const value = currentPrice !== null ? shares * currentPrice : null;
              const pnl = value !== null ? value - cost : null;
              const pnlPct = pnl !== null ? (pnl / cost) * 100 : null;
              const isDeepLoss = pnlPct !== null && pnlPct < -10;

              return (
                <tr
                  key={pos.id}
                  style={isDeepLoss ? { backgroundColor: "var(--color-loss-row-bg)" } : {}}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs text-gray-400">{pos.symbol}</span>
                    <br />
                    <span className="font-medium text-gray-800">{pos.name}</span>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">{shares.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right tabular-nums">¥{avgCost.toFixed(3)}</td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {currentPrice !== null ? (
                      <span>
                        ¥{currentPrice.toFixed(3)}
                        {pos.is_stale && (
                          <span className="ml-1 text-xs text-gray-400" title="数据可能过期">⚠</span>
                        )}
                        {pos.price_date && (
                          <span className="block text-xs text-gray-400">{pos.price_date}</span>
                        )}
                      </span>
                    ) : (
                      <span className="text-gray-300">--</span>
                    )}
                  </td>
                  <td className={`px-4 py-3 text-right tabular-nums font-medium ${pnl !== null ? pnlColor(pnl) : "text-gray-300"}`}>
                    {pnl !== null ? `${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}` : "--"}
                  </td>
                  <td className={`px-4 py-3 text-right tabular-nums font-medium ${pnlPct !== null ? pnlColor(pnlPct) : "text-gray-300"}`}>
                    {pnlPct !== null ? `${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(2)}%` : "--"}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-gray-600">
                    ¥{cost.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-gray-600">
                    {value !== null ? `¥${value.toFixed(2)}` : "--"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => setTradeTarget(pos)}
                      className="text-xs px-3 py-1 rounded-full border border-blue-200 text-blue-500 hover:bg-blue-50 transition-colors whitespace-nowrap"
                    >
                      记录交易
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {tradeTarget && (
        <RecordTradeModal
          position={tradeTarget}
          onClose={() => setTradeTarget(null)}
          onRecorded={onRefresh}
        />
      )}
    </>
  );
}

export function PortfolioTableSkeleton() {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-gray-500 text-xs uppercase tracking-wide">
            <th className="px-4 py-3 text-left">代码 / 名称</th>
            <th className="px-4 py-3 text-right">持仓量</th>
            <th className="px-4 py-3 text-right">均价</th>
            <th className="px-4 py-3 text-right">现价</th>
            <th className="px-4 py-3 text-right">盈亏金额</th>
            <th className="px-4 py-3 text-right">盈亏%</th>
            <th className="px-4 py-3 text-right">总成本</th>
            <th className="px-4 py-3 text-right">市值</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          <RowSkeleton />
          <RowSkeleton />
          <RowSkeleton />
        </tbody>
      </table>
    </div>
  );
}
