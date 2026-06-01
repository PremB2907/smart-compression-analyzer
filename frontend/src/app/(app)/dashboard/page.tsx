"use client";

import { useEffect, useState } from "react";
import { MetricCharts } from "@/components/charts/metric-charts";
import { getDashboard } from "@/lib/api";

export default function DashboardPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof getDashboard>> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div>
        <h2 className="text-2xl font-semibold text-white">Dashboard</h2>
        <p className="mt-4 text-amber-400">{error} — sign in to view your metrics.</p>
      </div>
    );
  }

  const cards = data?.cards;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold text-white">Analytics Dashboard</h2>
        <p className="text-slate-400">Google Analytics for document compression</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Total Files", value: cards?.total_files ?? 0 },
          { label: "Avg Compression", value: cards?.avg_compression_ratio?.toFixed(2) ?? "—" },
          { label: "Avg OCR Accuracy", value: cards?.avg_ocr_accuracy != null ? `${(cards.avg_ocr_accuracy * 100).toFixed(1)}%` : "—" },
          { label: "Avg BER", value: cards?.avg_ber != null ? `${(cards.avg_ber * 100).toFixed(2)}%` : "—" },
        ].map((c) => (
          <div key={c.label} className="card">
            <p className="text-xs text-slate-500">{c.label}</p>
            <p className="mt-1 text-2xl font-bold text-white">{c.value}</p>
          </div>
        ))}
      </div>

      {data && <MetricCharts charts={data.charts} />}

      {data?.leaderboard?.length ? (
        <div className="card">
          <h3 className="mb-4 font-medium text-white">Format Leaderboard</h3>
          <ol className="space-y-2">
            {data.leaderboard.map((row, i) => (
              <li key={row.format} className="flex justify-between text-sm text-slate-300">
                <span>
                  #{i + 1} {row.format}
                </span>
                <span className="font-mono text-brand-100">{row.score.toFixed(3)}</span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      {data?.formulas && (
        <div className="card">
          <h3 className="mb-3 font-medium text-white">Metric Formulas</h3>
          <dl className="grid gap-2 text-sm text-slate-400 md:grid-cols-2">
            {Object.entries(data.formulas).map(([k, v]) => (
              <div key={k}>
                <dt className="font-mono text-slate-300">{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
}
