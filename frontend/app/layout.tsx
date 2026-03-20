import type { Metadata } from "next";
import type { ReactNode } from "react";

import { PerformanceVitals } from "@/components/performance-vitals";
import { ThemeProvider } from "@/components/theme-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: "ADEA Control Center",
  description: "Modern pipeline operations dashboard for Autonomous Data Engineer Agent."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans">
        <ThemeProvider>
          <PerformanceVitals />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
