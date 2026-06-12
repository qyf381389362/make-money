"use client";

import React, { useMemo } from "react";
import { JournalEntry } from "../lib/api";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
  Cell
} from "recharts";

interface AiMetricsProps {
  entries: JournalEntry[];
}

export default function AiMetrics({ entries }: AiMetricsProps) {
  // 过滤出所有有 pnl 的已平仓记录 (Sell)
  const sellEntries = useMemo(() => entries.filter((e) => e.action === "sell"), [entries]);

  const { stats, totalSells, totalSellPnl, analyzingCount, radarData, pnlTrendData } = useMemo(() => {
    const currentStats: Record<string, { count: number; pnl: number }> = {
      "理性分析": { count: 0, pnl: 0 },
      "追涨杀跌": { count: 0, pnl: 0 },
      "贪婪": { count: 0, pnl: 0 },
      "恐慌": { count: 0, pnl: 0 },
      "其它": { count: 0, pnl: 0 },
    };
    
    let currentTotalPnl = 0;
    let currentAnalyzingCount = 0;

    sellEntries.forEach((entry) => {
      const pnlVal = entry.pnl ? parseFloat(entry.pnl) : 0;
      currentTotalPnl += pnlVal;

      const type = entry.motivation_type;
      if (!type) {
        currentAnalyzingCount += 1;
      } else if (currentStats[type]) {
        currentStats[type].count += 1;
        currentStats[type].pnl += pnlVal;
      } else {
        currentStats["其它"].count += 1;
        currentStats["其它"].pnl += pnlVal;
      }
    });

    // 构造雷达图数据
    const radar = [
      { subject: "理性", A: currentStats["理性分析"].count },
      { subject: "追高", A: currentStats["追涨杀跌"].count },
      { subject: "贪婪", A: currentStats["贪婪"].count },
      { subject: "恐慌", A: currentStats["恐慌"].count },
      { subject: "其它", A: currentStats["其它"].count },
    ];

    // 构造累计盈亏时间线数据
    const sortedSells = [...sellEntries].sort((a, b) => a.trade_date.localeCompare(b.trade_date));
    let accPnl = 0;
    const trend = sortedSells.map((e) => {
      accPnl += e.pnl ? parseFloat(e.pnl) : 0;
      return {
        date: e.trade_date,
        pnl: e.pnl ? parseFloat(e.pnl) : 0,
        cumulative: accPnl,
      };
    });

    return { 
      stats: currentStats, 
      totalSells: sellEntries.length, 
      totalSellPnl: currentTotalPnl, 
      analyzingCount: currentAnalyzingCount,
      radarData: radar,
      pnlTrendData: trend
    };
  }, [sellEntries]);

  // 计算理性交易比例，作为交易健康分
  const totalAnalyzed = totalSells - analyzingCount;
  const rationalCount = stats["理性分析"].count;
  const healthScore = totalAnalyzed > 0 ? Math.round((rationalCount / totalAnalyzed) * 100) : 100;

  const getHealthLevel = (score: number) => {
    if (score >= 80) return { label: "优秀 (理性克制)", desc: "交易系统完备，极少受情绪左右。", color: "text-emerald-500", shadow: "shadow-emerald-500/20" };
    if (score >= 60) return { label: "良好 (偶有情绪)", desc: "基本理性，偶有冲动交易，需保持警惕。", color: "text-yellow-500", shadow: "shadow-yellow-500/20" };
    return { label: "警告 (偏差严重)", desc: "情绪化交易明显，建议暂停交易并重新梳理逻辑。", color: "text-rose-500", shadow: "shadow-rose-500/20" };
  };

  const healthLevel = getHealthLevel(healthScore);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white/90 dark:bg-slate-800/90 backdrop-blur-md p-3 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl text-xs">
          <p className="font-semibold text-slate-700 dark:text-slate-300 mb-1">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={`item-${index}`} style={{ color: entry.color }} className="font-medium">
              {entry.name}: {entry.value > 0 ? "+" : ""}{entry.value.toFixed(2)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-6 mb-8">
      {/* 第一排：健康度卡片 + 雷达图 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* 健康度得分 */}
        <div className="lg:col-span-1 relative overflow-hidden rounded-3xl border border-slate-200/60 dark:border-slate-800/60 bg-gradient-to-br from-white to-slate-50 dark:from-slate-900/80 dark:to-slate-900/40 p-6 shadow-sm flex flex-col justify-between">
          <div className="relative z-10">
            <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-widest">交易心理健康度</h3>
            <div className="mt-6 flex items-baseline gap-2">
              <span className={`text-6xl font-black tracking-tighter ${healthLevel.color} drop-shadow-md`}>
                {totalAnalyzed > 0 ? healthScore : "--"}
              </span>
              <span className="text-xl font-bold text-slate-300 dark:text-slate-600">/ 100</span>
            </div>
            <div className="mt-4 flex items-center gap-2">
              <span className={`text-sm font-bold px-3 py-1 rounded-full bg-white dark:bg-slate-800 shadow-sm ${healthLevel.color}`}>
                {totalAnalyzed > 0 ? healthLevel.label : "暂无分析数据"}
              </span>
            </div>
            <p className="mt-3 text-sm text-slate-500 dark:text-slate-400 font-medium leading-relaxed">
              {totalAnalyzed > 0 ? healthLevel.desc : "请先记录带有交易原因的已实现(Sell)交易记录。"}
            </p>
          </div>
          
          {/* 装饰性背景光晕 */}
          <div className={`absolute -bottom-10 -right-10 w-48 h-48 bg-current opacity-5 blur-3xl rounded-full ${healthLevel.color}`} />
          
          {analyzingCount > 0 && (
            <div className="mt-6 relative z-10 p-3 rounded-xl bg-sky-50 dark:bg-sky-500/10 border border-sky-100 dark:border-sky-500/20 flex items-center gap-2 text-xs">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
              </span>
              <span className="text-sky-700 dark:text-sky-300 font-medium tracking-wide">
                有 {analyzingCount} 笔决策正在进行 AI 分析...
              </span>
            </div>
          )}
        </div>

        {/* 心理偏差雷达图 */}
        <div className="lg:col-span-1 rounded-3xl border border-slate-200/60 dark:border-slate-800/60 bg-white/50 dark:bg-slate-900/30 backdrop-blur-xl p-6 shadow-sm flex flex-col">
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-2">性格雷达 (频率分布)</h3>
          <div className="flex-1 w-full min-h-[200px]">
            {totalAnalyzed > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="#cbd5e1" strokeDasharray="3 3" opacity={0.3} />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 12, fontWeight: 600 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Radar name="交易次数" dataKey="A" stroke="#3b82f6" strokeWidth={2} fill="#3b82f6" fillOpacity={0.2} />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">暂无数据绘制雷达图</div>
            )}
          </div>
        </div>

        {/* 心理偏误盈亏柱状图 */}
        <div className="lg:col-span-1 rounded-3xl border border-slate-200/60 dark:border-slate-800/60 bg-white/50 dark:bg-slate-900/30 backdrop-blur-xl p-6 shadow-sm flex flex-col">
          <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-2">偏误盈亏榜 (元)</h3>
          <div className="flex-1 w-full min-h-[200px]">
            {totalAnalyzed > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={radarData.map(d => ({ name: d.subject, pnl: stats[d.subject === '理性' ? '理性分析' : d.subject === '追高' ? '追涨杀跌' : d.subject].pnl }))} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
                  <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} cursor={{fill: 'transparent'}} />
                  <Bar dataKey="pnl" radius={[4, 4, 4, 4]}>
                    {radarData.map((entry, index) => {
                      const val = stats[entry.subject === '理性' ? '理性分析' : entry.subject === '追高' ? '追涨杀跌' : entry.subject].pnl;
                      return <Cell key={`cell-${index}`} fill={val >= 0 ? '#ef4444' : '#10b981'} fillOpacity={0.8} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">暂无分析数据</div>
            )}
          </div>
        </div>
      </div>

      {/* 第二排：累计盈亏时间线 */}
      <div className="w-full rounded-3xl border border-slate-200/60 dark:border-slate-800/60 bg-white/50 dark:bg-slate-900/30 backdrop-blur-xl p-6 shadow-sm">
        <div className="flex justify-between items-end mb-6">
          <div>
            <h3 className="text-sm font-semibold text-slate-600 dark:text-slate-300">累计已实现盈亏趋势</h3>
            <p className="text-xs text-slate-400 mt-1">展示你所有闭环决策（卖出）带来的资金累计变化曲线</p>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-400 block mb-1">总已实现盈亏</span>
            <span className={`text-xl font-bold ${totalSellPnl >= 0 ? "text-rose-500" : "text-emerald-500"}`}>
              {totalSellPnl > 0 ? "+" : ""}{totalSellPnl.toFixed(2)}
            </span>
          </div>
        </div>
        
        <div className="w-full h-[240px]">
          {pnlTrendData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={pnlTrendData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorPnlGain" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorPnlLoss" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.15} />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} minTickGap={30} />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area 
                  type="monotone" 
                  dataKey="cumulative" 
                  name="累计盈亏" 
                  stroke={pnlTrendData[pnlTrendData.length-1]?.cumulative >= 0 ? "#ef4444" : "#10b981"} 
                  strokeWidth={3}
                  fill={pnlTrendData[pnlTrendData.length-1]?.cumulative >= 0 ? "url(#colorPnlGain)" : "url(#colorPnlLoss)"} 
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl">
              <span className="text-xs text-slate-400">记录第一笔卖出决策后，即可查看资金积累曲线</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
