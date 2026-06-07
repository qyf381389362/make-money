import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "持仓仪表板",
  description: "A 股持仓管理 + 决策日记",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className="h-full">
      <body className="min-h-full bg-[var(--background)]">{children}</body>
    </html>
  );
}
