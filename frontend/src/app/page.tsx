import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center px-6 text-center">
      <p className="mb-2 text-sm uppercase tracking-widest text-brand-100">SecureArchive AI</p>
      <h1 className="mb-4 text-5xl font-bold text-white">Compression. OCR. Integrity.</h1>
      <p className="mb-2 text-xl text-slate-300">All Verified.</p>
      <p className="mb-10 max-w-2xl text-slate-400">
        Research-grade SaaS for comparing JPEG, PNG, TIFF, PDF, WebP, and DjVu on storage
        efficiency, OCR preservation, hidden metadata survival, and archival suitability.
      </p>
      <div className="flex gap-4">
        <Button asChild size="lg">
          <Link href="/dashboard">Open Dashboard</Link>
        </Button>
        <Button asChild variant="outline" size="lg">
          <Link href="/upload">Analyze Documents</Link>
        </Button>
      </div>
    </main>
  );
}
