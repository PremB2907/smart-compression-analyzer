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
    <aside className="flex w-56 flex-col border-r-[3px] border-black bg-slate-950 p-4">
      <div className="mb-8 border-b-2 border-black pb-4">
        <p className="text-xs uppercase tracking-widest text-amber-400 font-bold">SecureArchive AI</p>
        <h1 className="text-lg font-black text-white font-outfit">Compression Lab</h1>
        <p className="text-xs text-slate-400">Compression. OCR. Integrity.</p>
      </div>
      <nav className="flex flex-1 flex-col gap-2">
        {links.map((l) => {
          const isActive = pathname === l.href;
          return (
            <Link
              key={l.href}
              href={l.href}
              className={`rounded-none px-3 py-2 text-sm font-bold border-2 border-black transition-all duration-100 ${
                isActive 
                  ? "bg-brand-500 text-white shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] translate-x-[-1px] translate-y-[-1px]" 
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              {l.label}
            </Link>
          );
        })}
      </nav>
      <Link href="/login" className="text-xs font-bold text-slate-400 hover:text-white mt-auto border-t border-black pt-4">
        Account Settings
      </Link>
    </aside>
  );
}
