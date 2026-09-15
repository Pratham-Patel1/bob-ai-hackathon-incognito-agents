import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SupplyChainOS — Control Tower",
  description: "AI-Powered Supply Chain Resilience & Digital Twin Control Tower",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
