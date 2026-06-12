"use client";
import { useState } from "react";
import { type Position } from "@/lib/api";
import RecordTradeModal from "./RecordTradeModal";

interface Props {
  positions: Position[];
  onRefresh: () => void;
  isRefreshing?: boolean;
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

export default function PortfolioTable({ positions, onRefresh, isRefreshing }: Props) {
  const [tradeTarget, setTradeTarget] = useState<Position | null>(null);

  return (
    <>
      <div className={`overflow-x-auto rounded-xl border border-gray-200 bg-white relative transition-opacity duration-300 ${isRefreshing ? "opacity-60 pointer-events-none" : ""}`}>
        {isRefreshing && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/40 z-10 backdrop-blur-[1px]">
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/95 shadow-sm border border-gray-100">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
              <span className="text-xs text-gray-600 font-medium">正在拉取最新行情...</span>
            </div>
          </div>
        )}
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-gray-500 text-xs uppercase tracking-wide">
              <th className="px-4 py-3 text-left">代码 / 名称</th>
              <th className="px-4 py-3 text-right">持仓量</th>
              <th className="px-4 py-3 text-right">均价</th>
              <th className="px-4 py-3 text-right">现价 / 净值</th>
              <th className="px-4 py-3 text-right">盈亏金额</th>
              <th className="px-4 py-3 text-right">盈亏%</th>
              <th className="px-4 py-3 text-right">总成本</th>
              <th className="px-4 py-3 text-right">市值 / 资产值</th>
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
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-xs text-gray-400">{pos.symbol}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                        pos.asset_type === "fund"
                          ? "bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-400"
                          : pos.asset_type === "etf"
                          ? "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400"
                          : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400"
                      }`}>
                        {pos.asset_type === "fund" ? "基金" : pos.asset_type === "etf" ? "ETF" : "股票"}
                      </span>
                    </div>
                    <span className="font-medium text-gray-800 dark:text-gray-200">{pos.name}</span>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">{shares.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    ¥{pos.asset_type === "fund" ? avgCost.toFixed(4) : avgCost.toFixed(3)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {currentPrice !== null ? (
                      <span>
                        ¥{pos.asset_type === "fund" ? currentPrice.toFixed(4) : currentPrice.toFixed(2)}
                        {pos.is_stale && (
                          <span className="ml-1 text-xs text-gray-400" title="行情数据超过1天未更新">⚠</span>
                        )}
                        {pos.price_date && (
                          <span className="block text-[10px] text-gray-400 mt-0.5">{pos.price_date}</span>
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
            <th className="px-4 py-3 text-right">现价 / 净值</th>
            <th className="px-4 py-3 text-right">盈亏金额</th>
            <th className="px-4 py-3 text-right">盈亏%</th>
            <th className="px-4 py-3 text-right">总成本</th>
            <th className="px-4 py-3 text-right">市值 / 资产值</th>
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
