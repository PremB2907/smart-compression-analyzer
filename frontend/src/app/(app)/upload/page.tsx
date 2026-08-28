"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import * as Progress from "@radix-ui/react-progress";
import { getAnalysis, getTaskStatus, getToken, uploadFiles } from "@/lib/api";

const ACCEPT = ".png,.jpg,.jpeg,.bmp,.tif,.tiff,.pdf";

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState(0);
  const [uploadIds, setUploadIds] = useState<number[]>([]);
  const [results, setResults] = useState<Record<number, unknown>>({});
  const [error, setError] = useState("");
  const [authenticated, setAuthenticated] = useState(true);

  useEffect(() => {
    setAuthenticated(!!getToken());
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const list = Array.from(e.dataTransfer.files).slice(0, 10);
    setFiles(list);
  }, []);

  const process = async () => {
    if (!files.length) return;
    setError("");
    setProgress(10);
    try {
      const res = await uploadFiles(files);
      const ids = res.uploads.map((u: { id: number }) => u.id);
      setUploadIds(ids);
      setProgress(30);

      for (const id of ids) {
        let done = false;
        while (!done) {
          const task = await getTaskStatus(id);
          if (task.status === "completed" || task.celery_state === "SUCCESS") {
            const analysis = await getAnalysis(id);
            setResults((r) => ({ ...r, [id]: analysis }));
            done = true;
          } else if (task.status === "failed") {
            done = true;
          } else {
            await new Promise((r) => setTimeout(r, 2000));
          }
        }
      }
      setProgress(100);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    }
  };

  if (!authenticated) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <div>
          <h2 className="text-2xl font-semibold text-white">Document Upload</h2>
          <p className="mt-4 text-amber-400">Not authenticated — sign in to upload files.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white">Document Upload</h2>
        <p className="text-slate-400">Up to 10 files, 50 MB each — PNG, TIFF, JPEG, BMP, PDF</p>
      </div>

      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        className="card flex min-h-[200px] cursor-pointer flex-col items-center justify-center border-dashed border-brand-500/40"
      >
        <p className="text-slate-300">Drag & drop files here</p>
        <input
          type="file"
          multiple
          accept={ACCEPT}
          className="mt-4 text-sm"
          onChange={(e) => setFiles(Array.from(e.target.files || []).slice(0, 10))}
        />
        {files.length > 0 && (
          <ul className="mt-4 text-xs text-slate-500">
            {files.map((f) => (
              <li key={f.name}>{f.name}</li>
            ))}
          </ul>
        )}
      </div>

      <Button onClick={process} disabled={!files.length}>
        Run Paper Pipeline
      </Button>

      {progress > 0 && (
        <Progress.Root className="h-2 overflow-hidden rounded-full bg-slate-800" value={progress}>
          <Progress.Indicator
            className="h-full bg-brand-500 transition-all"
            style={{ width: `${progress}%` }}
          />
        </Progress.Root>
      )}

      {error && <p className="text-red-400">{error}</p>}

      {uploadIds.map((id) => (
        <div key={id} className="card">
          <h3 className="font-medium text-white">Upload #{id}</h3>
          {results[id] ? (
            <pre className="mt-2 max-h-96 overflow-auto text-xs text-slate-400">
              {JSON.stringify(results[id], null, 2)}
            </pre>
          ) : (
            <p className="text-sm text-slate-500">Processing…</p>
          )}
        </div>
      ))}
    </div>
  );
}
