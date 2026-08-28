"use client";

import { useEffect, useState } from "react";
import { getAnalysis, listUploads } from "@/lib/api";

export default function DjVuPage() {
  const [uploads, setUploads] = useState<any[]>([]);
  const [selectedUploadId, setSelectedUploadId] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<any | null>(null);
  const [selectedCompareFormat, setSelectedCompareFormat] = useState<string>("JPEG");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load completed uploads
  useEffect(() => {
    listUploads()
      .then((data) => {
        const completed = data.filter((u) => u.status === "completed");
        setUploads(completed);
        if (completed.length > 0) {
          setSelectedUploadId(completed[0].id);
        }
      })
      .catch((err) => setError("Failed to load uploads: " + err.message));
  }, []);

  // Fetch analysis details when upload changes
  useEffect(() => {
    if (!selectedUploadId) return;
    setLoading(true);
    setError("");
    getAnalysis(selectedUploadId)
      .then((data) => {
        setAnalysis(data);
        setLoading(false);
      })
      .catch((err) => {
        setError("Failed to load analysis: " + err.message);
        setLoading(false);
      });
  }, [selectedUploadId]);

  const djvuMetric = analysis?.metrics.find((m: any) => m.format === "DjVu");
  const compareMetric = analysis?.metrics.find((m: any) => m.format === selectedCompareFormat);

  // Helper to render relative bar width
  const getBarWidth = (val1: number, val2: number, inverse = false) => {
    if (!val1 && !val2) return { w1: "0%", w2: "0%" };
    const maxVal = Math.max(val1 || 0.01, val2 || 0.01);
    const pct1 = ((val1 || 0) / maxVal) * 100;
    const pct2 = ((val2 || 0) / maxVal) * 100;
    return {
      w1: `${inverse ? 100 - pct1 : pct1}%`,
      w2: `${inverse ? 100 - pct2 : pct2}%`,
    };
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-white font-outfit">DjVu Intelligence Center</h2>
          <p className="text-slate-400">Deep-dive into DjVuLibre segmenting architecture & wavelet document compression</p>
        </div>

        {/* Upload selector */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-bold uppercase tracking-wider text-amber-400">Select Analyzed File</label>
          <select
            value={selectedUploadId || ""}
            onChange={(e) => setSelectedUploadId(Number(e.target.value))}
            className="w-64"
          >
            {uploads.length === 0 ? (
              <option value="">No completed uploads found</option>
            ) : (
              uploads.map((u) => (
                <option key={u.id} value={u.id}>
                  ID: {u.id} — {u.original_filename}
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-none border-2 border-black bg-red-950 p-4 text-red-200 shadow-[3px_3px_0px_0px_#000]">
          {error}
        </div>
      )}

      {/* Main architectural educational cards */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card card-purple">
          <h3 className="text-lg font-bold text-white font-outfit mb-2">Foreground Layer (JB2)</h3>
          <p className="text-sm text-slate-300">
            JB2 (JBIG2) compression isolates and clusters text glyphs. Instead of compressing every character pixel grid independently, it stores a library of unique glyph patterns and maps them across the page, resulting in sharp boundaries for high-accuracy OCR.
          </p>
        </div>
        <div className="card card-cyan">
          <h3 className="text-lg font-bold text-white font-outfit mb-2">Background Layer (IW44 Wavelet)</h3>
          <p className="text-sm text-slate-300">
            IW44 wavelet compression (c44 -slice 74) handles paper textures, photos, and continuous-tone elements. It compresses background noise aggressively, keeping details smooth and preventing quantization artifacts that are typical for JPEG algorithms.
          </p>
        </div>
        <div className="card card-green">
          <h3 className="text-lg font-bold text-white font-outfit mb-2">OCR Preservation Priority</h3>
          <p className="text-sm text-slate-300">
            Because text glyphs remain separated from background noise, the OCR engine is spared from artifact distortions. DjVu consistently outperforms lossy standards in retaining readability metrics on scanned documents.
          </p>
        </div>
        <div className="card card-orange">
          <h3 className="text-lg font-bold text-white font-outfit mb-2">Metadata Survival Check</h3>
          <p className="text-sm text-slate-300">
            Aggressive JPEG quantization frequently destroys hidden payload data (LSB). DjVu's structure preserves spatial/channel text integrity, allowing steganographic UUID and timestamp hashes to survive compression passes.
          </p>
        </div>
      </div>

      {/* Interactive Head-to-Head comparisons */}
      {loading ? (
        <div className="text-center py-12 text-slate-400">Loading analysis data...</div>
      ) : analysis && djvuMetric ? (
        <div className="card card-yellow space-y-6">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
            <h3 className="text-xl font-bold text-white font-outfit">Interactive Head-to-Head Compare</h3>
            
            <div className="flex items-center gap-3">
              <span className="font-bold text-slate-300 text-sm">Compare DjVu vs:</span>
              <select
                value={selectedCompareFormat}
                onChange={(e) => setSelectedCompareFormat(e.target.value)}
                className="w-40"
              >
                {analysis.metrics
                  .filter((m: any) => m.format !== "DjVu")
                  .map((m: any) => (
                    <option key={m.format} value={m.format}>
                      {m.format}
                    </option>
                  ))}
              </select>
            </div>
          </div>

          {compareMetric && (
            <div className="space-y-6">
              {/* Compression Ratio bar */}
              <div className="space-y-2 border-b border-black/35 pb-4">
                <div className="flex justify-between text-sm font-bold">
                  <span className="text-slate-300">Compression Ratio (Higher is better)</span>
                  <span className="text-green-400">DjVu: {djvuMetric.compression_ratio?.toFixed(2)}x vs {selectedCompareFormat}: {compareMetric.compression_ratio?.toFixed(2)}x</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono w-16 text-slate-400">DjVu</span>
                    <div className="flex-1 bg-slate-950 h-5 border border-black relative">
                      <div 
                        className="bg-brand-500 h-full border-r border-black" 
                        style={{ width: getBarWidth(djvuMetric.compression_ratio, compareMetric.compression_ratio).w1 }}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono w-16 text-slate-400">{selectedCompareFormat}</span>
                    <div className="flex-1 bg-slate-950 h-5 border border-black relative">
                      <div 
                        className="bg-purple-500 h-full border-r border-black" 
                        style={{ width: getBarWidth(djvuMetric.compression_ratio, compareMetric.compression_ratio).w2 }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* OCR Accuracy bar */}
              <div className="space-y-2 border-b border-black/35 pb-4">
                <div className="flex justify-between text-sm font-bold">
                  <span className="text-slate-300">OCR Accuracy (Higher is better)</span>
                  <span className="text-cyan-400">DjVu: {(djvuMetric.ocr_accuracy * 100).toFixed(2)}% vs {selectedCompareFormat}: {(compareMetric.ocr_accuracy * 100).toFixed(2)}%</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono w-16 text-slate-400">DjVu</span>
                    <div className="flex-1 bg-slate-950 h-5 border border-black relative">
                      <div 
                        className="bg-brand-500 h-full border-r border-black" 
                        style={{ width: getBarWidth(djvuMetric.ocr_accuracy, compareMetric.ocr_accuracy).w1 }}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono w-16 text-slate-400">{selectedCompareFormat}</span>
                    <div className="flex-1 bg-slate-950 h-5 border border-black relative">
                      <div 
                        className="bg-purple-500 h-full border-r border-black" 
                        style={{ width: getBarWidth(djvuMetric.ocr_accuracy, compareMetric.ocr_accuracy).w2 }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* BER bar */}
              <div className="space-y-2 pb-2">
                <div className="flex justify-between text-sm font-bold">
                  <span className="text-slate-300">Bit Error Rate (Lower is better)</span>
                  <span className="text-orange-400">DjVu: {(djvuMetric.ber * 100).toFixed(3)}% vs {selectedCompareFormat}: {(compareMetric.ber * 100).toFixed(3)}%</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono w-16 text-slate-400">DjVu</span>
                    <div className="flex-1 bg-slate-950 h-5 border border-black relative">
                      <div 
                        className="bg-brand-500 h-full border-r border-black" 
                        style={{ width: getBarWidth(djvuMetric.ber, compareMetric.ber).w1 }}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono w-16 text-slate-400">{selectedCompareFormat}</span>
                    <div className="flex-1 bg-slate-950 h-5 border border-black relative">
                      <div 
                        className="bg-purple-500 h-full border-r border-black" 
                        style={{ width: getBarWidth(djvuMetric.ber, compareMetric.ber).w2 }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card text-center py-12 text-slate-400">
          Please run a document upload pipeline first to see head-to-head DjVu analysis.
        </div>
      )}
    </div>
  );
}
