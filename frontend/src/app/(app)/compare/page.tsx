"use client";

import { useEffect, useState } from "react";
import { getAnalysis, listUploads } from "@/lib/api";

const API_HOST = "http://localhost:8000"; // Backend host to load local dev-storage files

export default function ComparePage() {
  const [uploads, setUploads] = useState<any[]>([]);
  const [selectedUploadId, setSelectedUploadId] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<any | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<string>("JPEG");
  const [split, setSplit] = useState(50);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load all user uploads on mount
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

  // Fetch analysis details when selected upload changes
  useEffect(() => {
    if (!selectedUploadId) return;
    setLoading(true);
    setError("");
    getAnalysis(selectedUploadId)
      .then((data) => {
        setAnalysis(data);
        const availableFormats = data.metrics.map((m: any) => m.format);
        if (availableFormats.length > 0) {
          setSelectedFormat(availableFormats[0]);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError("Failed to load analysis details: " + err.message);
        setLoading(false);
      });
  }, [selectedUploadId]);

  const currentMetric = analysis?.metrics.find((m: any) => m.format === selectedFormat);
  const originalUrl = analysis?.original_url ? `${API_HOST}${analysis.original_url}` : "";
  const reconstructedUrl = currentMetric?.reconstructed_url ? `${API_HOST}${currentMetric.reconstructed_url}` : "";

  return (
    <div className="space-y-8">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-white font-outfit">Visual Comparison Studio</h2>
          <p className="text-slate-400">Interactive split view slider, custom differences heatmap, and dynamic metrics comparison</p>
        </div>

        {/* Upload selector */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-bold uppercase tracking-wider text-amber-400">Select Uploaded Document</label>
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

      {loading && (
        <div className="text-center py-12 text-slate-400 font-medium">
          Loading comparison data...
        </div>
      )}

      {!loading && analysis && (
        <div className="grid gap-8 lg:grid-cols-3">
          {/* Controls & Metrics sidebar */}
          <div className="space-y-6 lg:col-span-1">
            <div className="card card-purple space-y-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-purple-400">Compression Format</label>
                <select
                  value={selectedFormat}
                  onChange={(e) => setSelectedFormat(e.target.value)}
                  className="mt-1 w-full"
                >
                  {analysis.metrics.map((m: any) => (
                    <option key={m.format} value={m.format}>
                      {m.format}
                    </option>
                  ))}
                </select>
              </div>

              {currentMetric && (
                <div className="pt-2 space-y-3">
                  <div className="flex justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400 font-medium">Compression Ratio</span>
                    <span className="font-bold text-green-400">{currentMetric.compression_ratio?.toFixed(2)}x</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400 font-medium">PSNR</span>
                    <span className="font-bold text-cyan-400">
                      {currentMetric.psnr ? `${currentMetric.psnr.toFixed(2)} dB` : "Lossless / Perfect"}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400 font-medium">SSIM</span>
                    <span className="font-bold text-yellow-400">{currentMetric.ssim?.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400 font-medium">OCR Accuracy</span>
                    <span className="font-bold text-brand-100">{(currentMetric.ocr_accuracy * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400 font-medium">BER (Stego Leak)</span>
                    <span className="font-bold text-orange-400">{(currentMetric.ber * 100).toFixed(3)}%</span>
                  </div>
                </div>
              )}
            </div>

            {/* OCR Diff view */}
            <div className="card card-green">
              <h3 className="text-lg font-bold text-white font-outfit mb-3">OCR Recovery Comparison</h3>
              <div className="space-y-3 text-xs">
                <div>
                  <span className="font-bold text-slate-400 block mb-1">Reference (Ground Truth)</span>
                  <div className="bg-slate-950 p-2 border border-black max-h-24 overflow-y-auto text-green-400 font-mono">
                    {analysis.ocr_by_format[selectedFormat]?.reference_text || "(No text detected)"}
                  </div>
                </div>
                <div>
                  <span className="font-bold text-slate-400 block mb-1">Recovered Text ({selectedFormat})</span>
                  <div className="bg-slate-950 p-2 border border-black max-h-24 overflow-y-auto text-brand-100 font-mono">
                    {analysis.ocr_by_format[selectedFormat]?.recovered_text || "(No text detected)"}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Interactive Zoom / Slider compare area */}
          <div className="space-y-6 lg:col-span-2">
            {/* Slider view card */}
            <div className="card card-blue">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-bold text-white font-outfit">Split-Screen Slider</h3>
                <span className="text-xs font-bold text-blue-400 px-2 py-0.5 border border-black bg-blue-950">
                  {split}% Original / {100 - split}% {selectedFormat}
                </span>
              </div>
              
              <input
                type="range"
                min={0}
                max={100}
                value={split}
                onChange={(e) => setSplit(Number(e.target.value))}
                className="w-full h-2 bg-slate-800 rounded-none border border-black appearance-none cursor-pointer accent-blue-500"
              />

              <div className="relative mt-4 h-96 w-full border-[3px] border-black bg-slate-950 overflow-hidden">
                {/* Original side (Left) */}
                <div 
                  className="absolute inset-y-0 left-0 overflow-hidden z-10 border-r-2 border-amber-500" 
                  style={{ width: `${split}%` }}
                >
                  <img 
                    src={originalUrl} 
                    alt="Original" 
                    className="absolute top-0 left-0 h-full w-auto max-w-none object-cover" 
                    style={{ width: "800px" }}
                  />
                  <div className="absolute bottom-2 left-2 bg-black/80 px-2 py-0.5 text-xs text-amber-400 font-bold border border-black">
                    Original
                  </div>
                </div>

                {/* Reconstructed side (Right) */}
                <div className="absolute inset-0">
                  <img 
                    src={reconstructedUrl || originalUrl} 
                    alt="Compressed" 
                    className="h-full w-auto max-w-none object-cover"
                    style={{ width: "800px" }}
                  />
                  <div className="absolute bottom-2 right-2 bg-black/80 px-2 py-0.5 text-xs text-blue-400 font-bold border border-black">
                    {selectedFormat} Reconstructed
                  </div>
                </div>
              </div>
            </div>

            {/* Difference heatmap card */}
            <div className="card card-yellow">
              <h3 className="text-lg font-bold text-white font-outfit mb-3">Difference Heatmap</h3>
              <p className="text-xs text-slate-400 mb-3">Pixel-by-pixel visual delta generated dynamically using content difference overlay</p>
              
              <div className="relative h-96 w-full border-[3px] border-black bg-slate-950 overflow-hidden">
                {/* Reconstructed base */}
                <img 
                  src={reconstructedUrl || originalUrl} 
                  alt="Compressed Base" 
                  className="absolute inset-0 h-full w-full object-contain"
                />
                {/* Original inverted difference blend */}
                <img 
                  src={originalUrl} 
                  alt="Difference Overlay" 
                  className="absolute inset-0 h-full w-full object-contain mix-blend-difference filter invert opacity-90"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {!loading && !analysis && (
        <div className="card text-center py-16 space-y-4">
          <p className="text-slate-400">Please upload and analyze a document first to activate Visual Comparison Studio.</p>
        </div>
      )}
    </div>
  );
}
