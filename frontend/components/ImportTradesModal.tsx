"use client";
import { useState } from "react";
import {
  api,
  type ParsedTrade,
  type PreviewResult,
  type CommitResult,
} from "@/lib/api";

interface Props {
  onClose: () => void;
  onImported: () => void;
}

const BROKERS = [{ value: "ths", label: "同花顺" }];

const STATUS_STYLE: Record<string, { label: string; cls: string }> = {
  ok: { label: "可导入", cls: "text-emerald-600 bg-emerald-50" },
  skip: { label: "跳过", cls: "text-gray-400 bg-gray-100" },
  error: { label: "异常", cls: "text-rose-600 bg-rose-50" },
};

export default function ImportTradesModal({ onClose, onImported }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [broker, setBroker] = useState("ths");
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [result, setResult] = useState<CommitResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function doPreview() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      setPreview(await api.import.preview(file, broker));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "解析失败");
    } finally {
      setBusy(false);
    }
  }

  async function doCommit() {
    if (!preview) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.import.commit(preview.rows);
      setResult(res);
      if (res.committed) onImported();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[85vh] flex flex-col">
        <div className="flex justify-between items-center px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">导入券商交割单</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        <div className="px-6 py-5 overflow-y-auto">
          {result ? (
            <Summary result={result} />
          ) : preview ? (
            <PreviewTable preview={preview} />
          ) : (
            <SelectStep file={file} broker={broker} onFile={setFile} onBroker={setBroker} />
          )}
          {error && <p className="mt-4 text-sm text-rose-500">{error}</p>}
        </div>

        <div className="flex gap-3 px-6 py-4 border-t">
          {result ? (
            <button onClick={onClose} className="ml-auto px-5 py-2 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600">
              完成
            </button>
          ) : preview ? (
            <>
              <button onClick={() => { setPreview(null); setError(""); }} className="px-5 py-2 rounded-lg border text-sm text-gray-600 hover:bg-gray-50">
                返回
              </button>
              <button
                onClick={doCommit}
                disabled={busy || preview.parsable_count === 0}
                className="ml-auto px-5 py-2 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 disabled:opacity-50"
              >
                {busy ? "导入中…" : `导入 ${preview.parsable_count} 笔`}
              </button>
            </>
          ) : (
            <>
              <button onClick={onClose} className="px-5 py-2 rounded-lg border text-sm text-gray-600 hover:bg-gray-50">
                取消
              </button>
              <button
                onClick={doPreview}
                disabled={busy || !file}
                className="ml-auto px-5 py-2 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 disabled:opacity-50"
              >
                {busy ? "解析中…" : "解析预览"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function SelectStep({ file, broker, onFile, onBroker }: {
  file: File | null;
  broker: string;
  onFile: (f: File | null) => void;
  onBroker: (b: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm text-gray-600 mb-1">券商格式</label>
        <select
          value={broker}
          onChange={(e) => onBroker(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          {BROKERS.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-sm text-gray-600 mb-1">交割单文件（CSV）</label>
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => onFile(e.target.files?.[0] ?? null)}
          className="w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-600 hover:file:bg-blue-100"
        />
        {file && <p className="mt-2 text-xs text-gray-400">已选择：{file.name}</p>}
      </div>
      <p className="text-xs text-gray-400 leading-relaxed">
        支持同花顺导出的成交流水 CSV（GBK 编码亦可）。导入会按成交编号自动去重，重复的交割单不会重复计入；费用（手续费 / 印花税 / 过户费）将计入成本。
      </p>
    </div>
  );
}

function PreviewTable({ preview }: { preview: PreviewResult }) {
  return (
    <div>
      <div className="flex gap-3 mb-4">
        <Stat label="可导入" value={preview.parsable_count} cls="text-emerald-600" />
        <Stat label="重复跳过" value={preview.dup_count} cls="text-gray-400" />
        <Stat label="异常" value={preview.error_count} cls="text-rose-600" />
      </div>
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              <th className="px-2 py-2 text-left">日期</th>
              <th className="px-2 py-2 text-left">代码</th>
              <th className="px-2 py-2 text-left">名称</th>
              <th className="px-2 py-2 text-center">方向</th>
              <th className="px-2 py-2 text-right">数量</th>
              <th className="px-2 py-2 text-right">价格</th>
              <th className="px-2 py-2 text-right">费用</th>
              <th className="px-2 py-2 text-left">状态</th>
            </tr>
          </thead>
          <tbody>
            {preview.rows.map((r) => <Row key={r.row_index} r={r} />)}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Row({ r }: { r: ParsedTrade }) {
  const st = STATUS_STYLE[r.status] ?? STATUS_STYLE.error;
  const dim = r.status !== "ok" ? "opacity-50" : "";
  return (
    <tr className={`border-t ${dim}`}>
      <td className="px-2 py-1.5">{r.trade_date ?? "—"}</td>
      <td className="px-2 py-1.5 font-mono">{r.symbol ?? "—"}</td>
      <td className="px-2 py-1.5">{r.name ?? "—"}</td>
      <td className="px-2 py-1.5 text-center">
        {r.action === "buy" ? <span className="text-rose-500">买入</span>
          : r.action === "sell" ? <span className="text-emerald-500">卖出</span> : "—"}
      </td>
      <td className="px-2 py-1.5 text-right tabular-nums">{r.shares ?? "—"}</td>
      <td className="px-2 py-1.5 text-right tabular-nums">{r.price ?? "—"}</td>
      <td className="px-2 py-1.5 text-right tabular-nums">{r.fee ?? "0"}</td>
      <td className="px-2 py-1.5">
        <span className={`px-1.5 py-0.5 rounded ${st.cls}`} title={r.note ?? ""}>{st.label}</span>
      </td>
    </tr>
  );
}

function Summary({ result }: { result: CommitResult }) {
  return (
    <div className="space-y-4">
      <div className="text-center py-4">
        <div className="text-4xl mb-2">{result.committed ? "✅" : "⚠️"}</div>
        <p className={`text-base font-semibold ${result.committed ? "text-gray-700" : "text-rose-600"}`}>
          {result.committed ? "导入完成" : "导入未提交，已整批回滚"}
        </p>
      </div>
      <div className="flex gap-3 justify-center">
        <Stat label="成功导入" value={result.imported} cls="text-emerald-600" />
        <Stat label="重复跳过" value={result.skipped_dup} cls="text-gray-400" />
        <Stat label="失败" value={result.failed.length} cls="text-rose-600" />
      </div>
      {result.failed.length > 0 && (
        <div className="border border-rose-100 bg-rose-50 rounded-lg p-3 text-xs text-rose-700">
          <p className="font-medium mb-1">失败行（整批已回滚，请修正后重试）：</p>
          <ul className="space-y-0.5">
            {result.failed.map((f) => <li key={f.row}>第 {f.row + 1} 行：{f.reason}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, cls }: { label: string; value: number; cls: string }) {
  return (
    <div className="flex-1 border rounded-lg px-3 py-2 text-center">
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className={`text-lg font-semibold tabular-nums ${cls}`}>{value}</p>
    </div>
  );
}
