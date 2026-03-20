"use client";

import { useEffect } from "react";
import { onCLS, onINP, onLCP, type Metric } from "web-vitals";

declare global {
  interface Window {
    __ADEA_WEB_VITALS__?: Metric[];
  }
}

function recordMetric(metric: Metric) {
  if (typeof window === "undefined") {
    return;
  }

  window.__ADEA_WEB_VITALS__ = [...(window.__ADEA_WEB_VITALS__ ?? []), metric];

  if (process.env.NODE_ENV !== "production") {
    console.info(`[WEB-VITALS] ${metric.name}: ${metric.value.toFixed(2)}`);
  }
}

export function PerformanceVitals() {
  useEffect(() => {
    onCLS(recordMetric);
    onINP(recordMetric);
    onLCP(recordMetric);
  }, []);

  return null;
}
