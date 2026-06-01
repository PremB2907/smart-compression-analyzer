"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/upload", label: "Upload" },
  { href: "/compare", label: "Visual Studio" },
  { href: "/djvu", label: "DjVu Center" },
  { href: "/research", label: "Research Mode" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-56 flex-col border-r border-slate-800 bg-slate-950/80 p-4">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-widest text-slate-500">SecureArchive AI</p>
        <h1 className="text-lg font-semibold text-white">Compression Lab</h1>
        <p className="text-xs text-slate-400">Compression. OCR. Integrity.</p>
      </div>
      <nav className="flex flex-1 flex-col gap-1">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`rounded-lg px-3 py-2 text-sm ${
              pathname === l.href ? "bg-brand-500/20 text-brand-100" : "text-slate-300 hover:bg-slate-800"
            }`}
          >
            {l.label}
          </Link>
        ))}
      </nav>
      <Link href="/login" className="text-xs text-slate-500 hover:text-slate-300">
        Account
      </Link>
    </aside>
  );
}
