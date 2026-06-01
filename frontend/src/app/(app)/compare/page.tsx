"use client";

import { useState } from "react";

export default function ComparePage() {
  const [split, setSplit] = useState(50);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white">Visual Comparison Studio</h2>
        <p className="text-slate-400">Split view, synchronized zoom, difference heatmap, OCR overlay</p>
      </div>

      <div className="card grid gap-4 lg:grid-cols-3">
        <div className="rounded-lg bg-slate-800 p-8 text-center text-slate-500">Original</div>
        <div className="rounded-lg bg-slate-800 p-8 text-center text-slate-500">Compressed</div>
        <div className="rounded-lg bg-slate-800 p-8 text-center text-slate-500">Difference Heatmap</div>
      </div>

      <div className="card">
        <label className="text-sm text-slate-400">Slider comparison</label>
        <input
          type="range"
          min={0}
          max={100}
          value={split}
          onChange={(e) => setSplit(Number(e.target.value))}
          className="mt-2 w-full"
        />
        <div className="mt-4 flex h-48 overflow-hidden rounded-lg">
          <div className="flex items-center justify-center bg-slate-800 text-slate-500" style={{ width: `${split}%` }}>
            Before
          </div>
          <div
            className="flex flex-1 items-center justify-center bg-slate-700 text-slate-500"
            style={{ width: `${100 - split}%` }}
          >
            After
          </div>
        </div>
      </div>

      <p className="text-xs text-slate-500">
        Upload and complete analysis to load format-specific reconstructed images from MinIO.
      </p>
    </div>
  );
}
