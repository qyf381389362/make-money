"use client";
import { useState } from "react";
import { api, type AssetType } from "@/lib/api";

interface Props {
  onClose: () => void;
  onAdded: () => void;
}

const ASSET_TYPES: { value: AssetType; label: string }[] = [
  { value: "stock", label: "A股" },
  { value: "etf", label: "ETF" },
  { value: "fund", label: "基金" },
];

export default function AddPositionModal({ onClose, onAdded }: Props) {
  const [form, setForm] = useState({
    symbol: "",
    name: "",
    asset_type: "stock" as AssetType,
    shares: "",
    avg_cost: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function set(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
    setError("");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.positions.create({
        symbol: form.symbol.trim(),
        name: form.name.trim(),
        asset_type: form.asset_type,
        shares: parseFloat(form.shares),
        avg_cost: parseFloat(form.avg_cost),
      });
      onAdded();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "添加失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <div className="flex justify-between items-center mb-5">
          <h2 className="text-lg font-semibold">添加持仓</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-gray-600 mb-1">代码</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="600584"
                value={form.symbol}
                onChange={(e) => set("symbol", e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">名称</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="长电科技"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-600 mb-1">类型</label>
            <div className="flex gap-2">
              {ASSET_TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => set("asset_type", t.value)}
                  className={`flex-1 py-2 rounded-lg text-sm border transition-colors ${
                    form.asset_type === t.value
                      ? "bg-blue-500 text-white border-blue-500"
                      : "border-gray-200 text-gray-600 hover:border-blue-300"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-gray-600 mb-1">持仓数量</label>
              <input
                type="number"
                min="0"
                step="1"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="100"
                value={form.shares}
                onChange={(e) => set("shares", e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">买入均价（元）</label>
              <input
                type="number"
                min="0"
                step="0.0001"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="85.92"
                value={form.avg_cost}
                onChange={(e) => set("avg_cost", e.target.value)}
                required
              />
            </div>
          </div>

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
              {loading ? "添加中…" : "确认添加"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
