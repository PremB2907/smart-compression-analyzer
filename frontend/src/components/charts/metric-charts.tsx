"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ChartData = Record<
  string,
  {
    avg_compression_ratio: number | null;
    avg_ocr_accuracy: number | null;
    avg_ber: number | null;
    avg_psnr: number | null;
    avg_ssim: number | null;
  }
>;

export function MetricCharts({ charts }: { charts: ChartData }) {
  const data = Object.entries(charts).map(([format, v]) => ({
    format,
    cr: v.avg_compression_ratio ?? 0,
    ocr: (v.avg_ocr_accuracy ?? 0) * 100,
    ber: (v.avg_ber ?? 0) * 100,
    psnr: v.avg_psnr ?? 0,
    ssim: v.avg_ssim ?? 0,
  }));

  if (!data.length) {
    return <p className="text-sm text-slate-400">Upload documents to populate charts.</p>;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="card h-72">
        <h3 className="mb-2 text-sm font-medium text-slate-300">Compression Ratio</h3>
        <ResponsiveContainer width="100%" height="90%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="format" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip />
            <Bar dataKey="cr" fill="#3b82f6" name="CR" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="card h-72">
        <h3 className="mb-2 text-sm font-medium text-slate-300">OCR Accuracy (%)</h3>
        <ResponsiveContainer width="100%" height="90%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="format" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip />
            <Bar dataKey="ocr" fill="#22c55e" name="OCR %" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="card h-72">
        <h3 className="mb-2 text-sm font-medium text-slate-300">BER (%)</h3>
        <ResponsiveContainer width="100%" height="90%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="format" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip />
            <Bar dataKey="ber" fill="#f97316" name="BER %" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="card h-72">
        <h3 className="mb-2 text-sm font-medium text-slate-300">PSNR & SSIM</h3>
        <ResponsiveContainer width="100%" height="90%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="format" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip />
            <Legend />
            <Bar dataKey="psnr" fill="#a855f7" name="PSNR" />
            <Bar dataKey="ssim" fill="#06b6d4" name="SSIM" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
