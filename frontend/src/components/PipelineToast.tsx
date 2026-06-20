import { useEffect, useState } from "react";
import type { PipelineResult } from "../types/api";

interface PipelineToastProps {
  result: PipelineResult | null;
}

export default function PipelineToast({ result }: PipelineToastProps) {
  const [visible, setVisible] = useState(false);
  const [shown, setShown] = useState<PipelineResult | null>(null);

  // Track new result separately so the timer effect doesn't re-run on its own setState
  useEffect(() => {
    if (!result || result === shown) return;
    setShown(result);
  }, [result, shown]);

  // Start/reset the 3s dismiss timer whenever a new result is displayed
  useEffect(() => {
    if (!shown) return;
    setVisible(true);
    const timer = setTimeout(() => setVisible(false), 3000);
    return () => clearTimeout(timer);
  }, [shown]);

  if (!visible || !shown) return null;

  const success = shown.approved;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-opacity ${
        success ? "bg-green-800 text-green-100" : "bg-red-800 text-red-100"
      }`}
    >
      <span>{success ? "✓" : "✗"}</span>
      <span>
        {success
          ? `Ticket ${shown.ticket_id} terminé en ${shown.rounds} tour${shown.rounds > 1 ? "s" : ""}`
          : `Pipeline échoué — ${shown.final_status}`}
      </span>
    </div>
  );
}
