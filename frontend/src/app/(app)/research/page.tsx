"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { getBenchmark, startBenchmark } from "@/lib/api";

const TABLE_LABELS = [
  "Table I — Compression Quality",
  "Table II — OCR Preservation",
  "Table III — Hidden Data",
  "Table IV — Timing",
  "Table V — Archival Ranking",
];

export default function ResearchPage() {
  const [benchId, setBenchId] = useState<number | null>(null);
  const [tables, setTables] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const res = await startBenchmark();
      setBenchId(res.benchmark_id);
      const poll = async () => {
        const b = await getBenchmark(res.benchmark_id);
        if (b.status === "completed") {
          setTables(b.tables || {});
          setLoading(false);
        } else {
          setTimeout(poll, 3000);
        }
      };
      poll();
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white">Research Reproduction Mode</h2>
        <p className="text-slate-400">
          Batch benchmark on demo dataset — auto-generates Tables I–V from paper methodology
        </p>
      </div>

      <Button onClick={run} disabled={loading}>
        {loading ? "Running benchmark…" : "Run Paper Benchmark"}
      </Button>

      {benchId && <p className="text-sm text-slate-500">Benchmark ID: {benchId}</p>}

      <div className="space-y-4">
        {TABLE_LABELS.map((label) => (
          <div key={label} className="card">
            <h3 className="font-medium text-white">{label}</h3>
            <pre className="mt-2 max-h-48 overflow-auto text-xs text-slate-400">
              {JSON.stringify(tables[label.toLowerCase().replace(/ /g, "_")] || tables, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}
