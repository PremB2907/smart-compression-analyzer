const comparisons = [
  { pair: "DjVu vs JPEG", focus: "OCR on printed text, halftone backgrounds" },
  { pair: "DjVu vs WebP", focus: "Lossy wavelet vs IW44 background layer" },
  { pair: "DjVu vs PDF", focus: "JPEG2000 stream vs JB2 foreground" },
];

export default function DjVuPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold text-white">DjVu Intelligence Center</h2>
        <p className="text-slate-400">Educational deep-dive into DjVuLibre IW44 + JB2 architecture</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="font-medium text-white">Foreground Layer</h3>
          <p className="mt-2 text-sm text-slate-400">
            JB2 (JBIG2) compression encodes bilevel text and line art with exceptional efficiency
            for scanned documents. Preserves sharp character boundaries critical for OCR.
          </p>
        </div>
        <div className="card">
          <h3 className="font-medium text-white">Background Layer</h3>
          <p className="mt-2 text-sm text-slate-400">
            IW44 wavelet compression (c44 -slice 74) handles continuous-tone regions, photographs,
            and paper texture at ~19× compression ratio in the paper benchmark.
          </p>
        </div>
        <div className="card">
          <h3 className="font-medium text-white">OCR Preservation</h3>
          <p className="mt-2 text-sm text-slate-400">
            DjVu achieves among the highest OCR character accuracy in the comparative study because
            text remains separated from background degradation.
          </p>
        </div>
        <div className="card">
          <h3 className="font-medium text-white">Metadata Survival</h3>
          <p className="mt-2 text-sm text-slate-400">
            LSB payload recovery depends on lossy paths; DjVu maintains low BER relative to
            aggressive JPEG quantization.
          </p>
        </div>
      </div>

      <div className="card">
        <h3 className="mb-4 font-medium text-white">Interactive Comparisons</h3>
        <div className="space-y-3">
          {comparisons.map((c) => (
            <div key={c.pair} className="rounded-lg border border-slate-700 p-4">
              <p className="font-medium text-brand-100">{c.pair}</p>
              <p className="text-sm text-slate-400">{c.focus}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
