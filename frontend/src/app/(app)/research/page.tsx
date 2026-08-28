"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { getBenchmark, startBenchmark } from "@/lib/api";

const TABLE_KEYS = [
  "table_i_compression_quality",
  "table_ii_ocr_preservation",
  "table_iii_hidden_data",
  "table_iv_timing",
  "table_v_archival_ranking",
];

const TABLE_METADATA: Record<string, { title: string; headers: string[]; keys: string[] }> = {
  table_i_compression_quality: {
    title: "Table I — Compression Quality Overview",
    headers: ["Format", "CR (Ratio)", "PSNR (dB)", "SSIM", "OCR Acc (%)", "BER (%)", "Payload Rec (%)"],
    keys: ["Format", "CR", "PSNR (dB)", "SSIM", "OCR Acc", "BER", "Payload %"],
  },
  table_ii_ocr_preservation: {
    title: "Table II — OCR Preservation Ranking",
    headers: ["Format", "CR (Ratio)", "PSNR (dB)", "SSIM", "OCR Acc (%)", "BER (%)", "Payload Rec (%)"],
    keys: ["Format", "CR", "PSNR (dB)", "SSIM", "OCR Acc", "BER", "Payload %"],
  },
  table_iii_hidden_data: {
    title: "Table III — Hidden Data (Stego BER) Survival",
    headers: ["Format", "CR (Ratio)", "PSNR (dB)", "SSIM", "OCR Acc (%)", "BER (%)", "Payload Rec (%)"],
    keys: ["Format", "CR", "PSNR (dB)", "SSIM", "OCR Acc", "BER", "Payload %"],
  },
  table_iv_timing: {
    title: "Table IV — Coding Efficiency & Throughput",
    headers: ["Format", "Encode Time (ms)", "Decode Time (ms)", "Throughput (MB/s)"],
    keys: ["Format", "Encode (ms)", "Decode (ms)", "Throughput (MB/s)"],
  },
  table_v_archival_ranking: {
    title: "Table V — Final Archival Utility Score",
    headers: ["Format", "Utility Score"],
    keys: ["format", "score"],
  },
};

export default function ResearchPage() {
  const [benchId, setBenchId] = useState<number | null>(null);
  const [tables, setTables] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    setLoading(true);
    setError("");
    setTables({});
    try {
      const res = await startBenchmark();
      setBenchId(res.benchmark_id);
      const poll = async () => {
        try {
          const b = await getBenchmark(res.benchmark_id);
          if (b.status === "completed") {
            setTables(b.tables || {});
            setLoading(false);
          } else {
            setTimeout(poll, 2000);
          }
        } catch (err: any) {
          setError("Failed to fetch benchmark progress: " + err.message);
          setLoading(false);
        }
      };
      poll();
    } catch (err: any) {
      setError("Failed to start benchmark: " + err.message);
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-extrabold tracking-tight text-white font-outfit">Research Reproduction Mode</h2>
        <p className="text-slate-400">
          Executes the complete paper methodology batch benchmark on the demo dataset to regenerate Tables I–V.
        </p>
      </div>

      <div className="flex items-center gap-4">
        <Button onClick={run} disabled={loading} className="px-6 h-12 bg-amber-500 hover:bg-amber-600 text-black border-2 border-black shadow-[3px_3px_0px_0px_#000]">
          {loading ? "Running benchmark…" : "Run Batch Benchmark"}
        </Button>
        {benchId && (
          <span className="text-xs font-bold text-slate-400 px-3 py-1 border border-black bg-slate-900 shadow-[1px_1px_0px_0px_#000]">
            Benchmark ID: {benchId}
          </span>
        )}
      </div>

      {error && (
        <div className="rounded-none border-2 border-black bg-red-950 p-4 text-red-200 shadow-[3px_3px_0px_0px_#000]">
          {error}
        </div>
      )}

      {loading && (
        <div className="card card-orange text-center py-12 space-y-4">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-r-2 border-orange-500 mr-3"></div>
          <p className="text-slate-300 font-medium">Running pipeline over dataset image files. This takes about 5-10 seconds...</p>
        </div>
      )}

      <div className="space-y-8">
        {TABLE_KEYS.map((key) => {
          const meta = TABLE_METADATA[key];
          const rows = tables[key] || [];

          return (
            <div key={key} className="card card-blue space-y-4">
              <h3 className="text-lg font-bold text-white font-outfit">{meta.title}</h3>
              
              {rows.length === 0 ? (
                <p className="text-sm text-slate-500 italic">No benchmark data loaded yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="brutalist-table">
                    <thead>
                      <tr>
                        {meta.headers.map((h) => (
                          <th key={h}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row: any, idx: number) => (
                        <tr key={idx}>
                          {meta.keys.map((k) => {
                            const val = row[k];
                            return (
                              <td key={k} className="font-mono">
                                {typeof val === "number"
                                  ? val % 1 === 0
                                    ? val.toLocaleString()
                                    : val.toFixed(k === "BER" ? 3 : 2)
                                  : val ?? "N/A"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
