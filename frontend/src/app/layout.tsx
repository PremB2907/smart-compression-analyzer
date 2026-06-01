import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecureArchive AI",
  description: "Compression. OCR. Integrity. All Verified.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
