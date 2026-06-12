"use client";

import React, { useState, useEffect } from "react";
import { type JournalEntry } from "@/lib/api";

interface Props {
  entries: JournalEntry[];
  filterSymbol: string;
  onFilterChange: (s: string) => void;
  onRefresh: () => void;
}

export default function JournalList({ entries, filterSymbol, onFilterChange, onRefresh }: Props) {
  const [searchText, setSearchText] = useState("");
  const [debouncedSearchText, setDebouncedSearchText] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  // Debounce 模糊搜索输入，防止过度重绘和打字卡顿
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchText(searchText);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchText]);

  // 当外部 filterSymbol 变化时，清空内部的搜索文本
  useEffect(() => {
    if (filterSymbol) {
      setSearchText("");
      setDebouncedSearchText("");
    }
  }, [filterSymbol]);

  // 根据所有筛选条件过滤交易记录
  const filteredEntries = entries.filter((entry) => {
    // 1. 模糊匹配原因及代码
    if (debouncedSearchText) {
      const reason = entry.reason?.toLowerCase() ?? "";
      const symbol = entry.symbol.toLowerCase();
      const query = debouncedSearchText.toLowerCase();
      if (!reason.includes(query) && !symbol.includes(query)) {
        return false;
      }
    }

    // 2. 过滤开始日期
    if (startDate && entry.trade_date < startDate) {
      return false;
    }

    // 3. 过滤结束日期
    if (endDate && entry.trade_date > endDate) {
      return false;
    }

    return true;
  });

  // 清空所有本地和全局筛选条件
  const handleClearAll = () => {
    setSearchText("");
    setDebouncedSearchText("");
    setStartDate("");
    setEndDate("");
    onFilterChange("");
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定要删除这条日记吗？")) return;
    try {
      // 引入 api 从顶部
      const { api } = await import("@/lib/api");
      await api.journal.delete(id);
      onRefresh();
    } catch (e: any) {
      alert("删除失败: " + e.message);
    }
  };

  const isFiltered = filterSymbol || searchText || startDate || endDate;

  return (
    <div className="space-y-4">
      {/* 筛选过滤工具栏 */}
      <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 backdrop-blur flex flex-col md:flex-row md:items-center gap-3 shadow-sm">
        {/* 模糊搜索 */}
        <div className="flex-1">
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="搜索股票代码、交易动机或评价内容..."
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-800 bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
          />
        </div>

        {/* 开始/结束日期 */}
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-800 bg-transparent text-slate-600 dark:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
          />
          <span className="text-xs text-slate-400">至</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-800 bg-transparent text-slate-600 dark:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
          />
        </div>

        {/* 清除按钮 */}
        {isFiltered && (
          <button
            onClick={handleClearAll}
            className="px-3 py-2 text-xs font-medium text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition whitespace-nowrap"
          >
            重置筛选
          </button>
        )}
      </div>

      {/* 列表显示 */}
      {filteredEntries.length === 0 ? (
        <div className="text-center text-slate-400 py-16 border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl">
          {isFiltered ? "未找到符合过滤条件的交易记录" : "还没有交易记录"}
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEntries.map((entry) => {
            const isBuy = entry.action === "buy";
            const pnl = entry.pnl ? parseFloat(entry.pnl) : null;

            // 心理偏误标签颜色主题映射
            const tagColors: Record<string, string> = {
              "理性分析": "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900/30",
              "追涨杀跌": "bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-900/30",
              "贪婪": "bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-900/30",
              "恐慌": "bg-violet-50 text-violet-600 border-violet-200 dark:bg-violet-950/40 dark:text-violet-400 dark:border-violet-900/30",
              "其它": "bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-900/40 dark:text-slate-400 dark:border-slate-800",
            };

            const tagClass = entry.motivation_type && tagColors[entry.motivation_type]
              ? tagColors[entry.motivation_type]
              : tagColors["其它"];

            return (
              <div
                key={entry.id}
                className="bg-white dark:bg-slate-900/30 rounded-2xl border border-slate-200/60 dark:border-slate-800/80 px-5 py-4 flex flex-col gap-3 shadow-sm hover:shadow-md transition-shadow duration-300"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    <span
                      className={`shrink-0 text-xs font-bold px-2.5 py-1 rounded-full ${
                        isBuy
                          ? "bg-red-50 text-[var(--color-gain)] dark:bg-red-950/20"
                          : "bg-green-50 text-[var(--color-loss)] dark:bg-green-950/20"
                      }`}
                    >
                      {isBuy ? "买入" : "卖出"}
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-slate-800 dark:text-slate-200">{entry.symbol}</span>
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          {parseFloat(entry.shares).toLocaleString()} 股 · ¥{parseFloat(entry.price).toFixed(3)}
                        </span>
                        {pnl !== null && (
                          <span
                            className={`text-sm font-semibold ${pnl >= 0 ? "text-[var(--color-gain)]" : "text-[var(--color-loss)]"}`}
                          >
                            {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)} 元
                          </span>
                        )}
                        {entry.motivation_type && (
                          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${tagClass}`}>
                            {entry.motivation_type}
                          </span>
                        )}
                      </div>
                      
                      {entry.reason && (
                        <p className="text-sm text-slate-600 dark:text-slate-300 mt-2 bg-slate-50/50 dark:bg-slate-950/30 p-2.5 rounded-lg border border-slate-100 dark:border-slate-900/50 whitespace-pre-wrap leading-relaxed">
                          {entry.reason}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="text-xs text-slate-400 shrink-0 text-left sm:text-right flex sm:flex-col justify-between sm:justify-start gap-1">
                    <div className="flex items-center gap-2 justify-end">
                      <div className="font-medium">{entry.trade_date}</div>
                      <button 
                        onClick={() => handleDelete(entry.id)} 
                        className="text-slate-300 hover:text-red-500 transition"
                        title="删除这条记录"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </button>
                    </div>
                    {entry.avg_cost_at_time && (
                      <div className="text-[10px] text-slate-500">
                        前均价 ¥{parseFloat(entry.avg_cost_at_time).toFixed(3)}
                      </div>
                    )}
                  </div>
                </div>

                {/* AI 心理审计点评意见 */}
                {entry.ai_audit && (
                  <div className="mt-1 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/50 border border-slate-100 dark:border-slate-900/80 text-xs text-slate-600 dark:text-slate-300">
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 dark:text-slate-500 mb-1.5 uppercase tracking-wider">
                      🤖 AI 决策心理审计点评
                    </div>
                    <p className="leading-relaxed font-normal">{entry.ai_audit}</p>
                  </div>
                )}

                {/* AI 审计进行中状态 */}
                {!entry.motivation_type && entry.reason && (
                  <div className="mt-1 p-3.5 rounded-xl bg-sky-50/30 dark:bg-sky-950/10 border border-sky-100/10 text-xs text-sky-600/80 animate-pulse italic flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-500 animate-ping" />
                    <span>AI 正在审计评估本交易的心理偏误，请稍后...</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
