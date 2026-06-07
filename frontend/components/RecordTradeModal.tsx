"use client";
import { useState } from "react";
import { api, type Action, type Position } from "@/lib/api";

interface Props {
  position: Position;
  onClose: () => void;
  onRecorded: () => void;
}

export default function RecordTradeModal({ position, onClose, onRecorded }: Props) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    action: "buy" as Action,
    shares: "",
    price: "",
    reason: "",
    trade_date: today,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function set(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
    setError("");
  }

  const previewPnl =
    form.action === "sell" && form.shares && form.price
      ? ((parseFloat(form.price) - parseFloat(position.avg_cost)) * parseFloat(form.shares)).toFixed(2)
      : null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.journal.create({
        symbol: position.symbol,
        action: form.action,
        shares: parseFloat(form.shares),
        price: parseFloat(form.price),
        reason: form.reason || undefined,
        trade_date: form.trade_date,
      });
      onRecorded();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "记录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <div className="flex justify-between items-center mb-1">
          <h2 className="text-lg font-semibold">记录交易</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>
        <p className="text-sm text-gray-500 mb-5">
          {position.name}（{position.symbol}）· 当前持仓 {position.shares} 股 · 均价 ¥{parseFloat(position.avg_cost).toFixed(3)}
        </p>

        <form onSubmit={submit} className="space-y-4">
          <div className="flex gap-2">
            {(["buy", "sell"] as Action[]).map((a) => (
              <button
                key={a}
                type="button"
                onClick={() => set("action", a)}
                className={`flex-1 py-2 rounded-lg text-sm border font-medium transition-colors ${
                  form.action === a
                    ? a === "buy"
                      ? "bg-[var(--color-gain)] text-white border-[var(--color-gain)]"
                      : "bg-[var(--color-loss)] text-white border-[var(--color-loss)]"
                    : "border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                {a === "buy" ? "买入" : "卖出"}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-gray-600 mb-1">数量（股）</label>
              <input
                type="number"
                min="1"
                step="1"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="100"
                value={form.shares}
                onChange={(e) => set("shares", e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">价格（元）</label>
              <input
                type="number"
                min="0"
                step="0.0001"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="78.50"
                value={form.price}
                onChange={(e) => set("price", e.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-600 mb-1">交易日期</label>
            <input
              type="date"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              value={form.trade_date}
              onChange={(e) => set("trade_date", e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-sm text-gray-600 mb-1">操作原因（可选）</label>
            <textarea
              rows={3}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
              placeholder="为什么做这笔交易？"
              value={form.reason}
              onChange={(e) => set("reason", e.target.value)}
            />
          </div>

          {previewPnl !== null && (
            <div className={`text-sm rounded-lg px-3 py-2 ${parseFloat(previewPnl) >= 0 ? "bg-red-50 text-[var(--color-gain)]" : "bg-green-50 text-[var(--color-loss)]"}`}>
              预计盈亏：{parseFloat(previewPnl) >= 0 ? "+" : ""}{previewPnl} 元
            </div>
          )}

          {error && <p className="text-sm text-red-500">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 rounded-lg border text-sm text-gray-600 hover:bg-gray-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 disabled:opacity-50"
            >
              {loading ? "提交中…" : "确认记录"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
