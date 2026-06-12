"use client";
import { useCallback, useEffect, useState } from "react";
import { api, type JournalEntry, type Position } from "@/lib/api";
import PortfolioTable, { PortfolioTableSkeleton } from "@/components/PortfolioTable";
import JournalList from "@/components/JournalList";
import AddPositionModal from "@/components/AddPositionModal";
import AiMetrics from "@/components/AiMetrics";
import ImportTradesModal from "@/components/ImportTradesModal";

type LoadState = "loading" | "ready" | "error";

export default function Dashboard() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [refreshing, setRefreshing] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [filterSymbol, setFilterSymbol] = useState("");
  const [refreshMsg, setRefreshMsg] = useState("");

  const load = useCallback(async () => {
    try {
      const [pos, jour] = await Promise.all([api.positions.list(), api.journal.list()]);
      setPositions(pos);
      setJournal(jour);
      setLoadState("ready");
    } catch {
      setLoadState("error");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // 轮询机制：如果有日记提交了 reason 但还没有 motivation_type（说明后台正在 AI 审计），则每 3 秒刷新一次数据
  useEffect(() => {
    const hasPendingAudit = journal.some((entry) => entry.reason && !entry.motivation_type);
    if (!hasPendingAudit) return;

    const intervalId = setInterval(async () => {
      try {
        const jour = await api.journal.list();
        setJournal(jour);
      } catch (e) {
        console.error("Polling journal failed", e);
      }
    }, 3000);

    return () => clearInterval(intervalId);
  }, [journal]);

  async function handleRefreshPrices() {
    setRefreshing(true);
    setRefreshMsg("");
    try {
      const result = await api.prices.refresh();
      setRefreshMsg(`已更新 ${result.updated} 只，跳过 ${result.skipped} 只${result.errors.length ? `，${result.errors.length} 只失败` : ""}`);
      await load();
    } catch (e: unknown) {
      setRefreshMsg(e instanceof Error ? e.message : "刷新失败");
    } finally {
      setRefreshing(false);
    }
  }

  // 汇总数据
  const totalCost = positions.reduce((s, p) => s + parseFloat(p.shares) * parseFloat(p.avg_cost), 0);
  const totalValue = positions.reduce((s, p) => {
    const price = p.current_price ? parseFloat(p.current_price) : parseFloat(p.avg_cost);
    return s + parseFloat(p.shares) * price;
  }, 0);
  const totalPnl = positions.length > 0 ? totalValue - totalCost : null;
  const totalPnlPct = totalPnl !== null && totalCost > 0 ? (totalPnl / totalCost) * 100 : null;

  const filteredJournal = filterSymbol
    ? journal.filter((e) => e.symbol === filterSymbol)
    : journal;

  return (
    <main className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      {/* 顶部横幅 */}
      <div className="bg-white rounded-2xl border border-gray-200 px-6 py-5 flex flex-col sm:flex-row sm:items-center gap-6">
        <div className="flex-1 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Stat label="总成本" value={`¥${totalCost.toFixed(2)}`} />
          <Stat label="总市值" value={positions.length > 0 ? `¥${totalValue.toFixed(2)}` : "--"} />
          <Stat
            label="总盈亏"
            value={totalPnl !== null ? `${totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(2)}` : "--"}
            color={totalPnl !== null ? (totalPnl >= 0 ? "gain" : "loss") : "neutral"}
          />
          <Stat
            label="盈亏比例"
            value={totalPnlPct !== null ? `${totalPnlPct >= 0 ? "+" : ""}${totalPnlPct.toFixed(2)}%` : "--"}
            color={totalPnlPct !== null ? (totalPnlPct >= 0 ? "gain" : "loss") : "neutral"}
          />
        </div>

        <div className="flex gap-2 shrink-0">
          <button
            onClick={() => setShowAdd(true)}
            className="px-4 py-2 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors"
          >
            + 添加持仓
          </button>
          <button
            onClick={() => setShowImport(true)}
            className="px-4 py-2 rounded-lg border border-blue-200 text-sm text-blue-600 hover:bg-blue-50 transition-colors"
          >
            导入交割单
          </button>
          <button
            onClick={handleRefreshPrices}
            disabled={refreshing || positions.length === 0}
            className="px-4 py-2 rounded-lg border text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors"
          >
            {refreshing ? "刷新中…" : "刷新价格"}
          </button>
        </div>
      </div>

      {refreshMsg && (
        <p className="text-sm text-gray-500 -mt-4">{refreshMsg}</p>
      )}

      {loadState === "ready" && (
        <AiMetrics entries={journal} />
      )}

      {/* 持仓表格 */}
      <section>
        <h2 className="text-base font-semibold text-gray-700 mb-3">持仓</h2>
        {loadState === "loading" && <PortfolioTableSkeleton />}
        {loadState === "error" && (
          <div className="text-center py-16 text-gray-400">
            加载失败，<button onClick={load} className="text-blue-500 underline">重试</button>
          </div>
        )}
        {loadState === "ready" && positions.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            还没有持仓，
            <button onClick={() => setShowAdd(true)} className="text-blue-500 underline">
              添加第一笔持仓
            </button>
          </div>
        )}
        {loadState === "ready" && positions.length > 0 && (
          <PortfolioTable
            positions={positions}
            onRefresh={load}
            isRefreshing={refreshing}
          />
        )}
      </section>

      {/* 决策日记 */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-gray-700">决策日记</h2>
          {filterSymbol && (
            <button
              onClick={() => setFilterSymbol("")}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              清除筛选
            </button>
          )}
        </div>
        <JournalList
          entries={filteredJournal}
          filterSymbol={filterSymbol}
          onFilterChange={setFilterSymbol}
          onRefresh={load}
        />
      </section>

      {showAdd && (
        <AddPositionModal
          onClose={() => setShowAdd(false)}
          onAdded={load}
        />
      )}

      {showImport && (
        <ImportTradesModal
          onClose={() => setShowImport(false)}
          onImported={load}
        />
      )}
    </main>
  );
}

function Stat({
  label,
  value,
  color = "neutral",
}: {
  label: string;
  value: string;
  color?: "gain" | "loss" | "neutral";
}) {
  const colorClass =
    color === "gain"
      ? "text-[var(--color-gain)]"
      : color === "loss"
      ? "text-[var(--color-loss)]"
      : "text-gray-800";

  return (
    <div>
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-lg font-semibold tabular-nums ${colorClass}`}>{value}</p>
    </div>
  );
}
