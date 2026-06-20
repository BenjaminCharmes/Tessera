import { useState } from "react";
import { api } from "../lib/api";
import type { PipelineResult } from "../types/api";

export interface UsePipelineResult {
  run: (ticketId: string) => void;
  running: Set<string>;
  results: Map<string, PipelineResult>;
}

export function usePipeline(projectId: string | null): UsePipelineResult {
  const [running, setRunning] = useState<Set<string>>(new Set());
  const [results, setResults] = useState<Map<string, PipelineResult>>(
    new Map(),
  );

  function run(ticketId: string) {
    if (!projectId) return;

    setRunning((prev) => {
      if (prev.has(ticketId)) return prev;
      return new Set([...prev, ticketId]);
    });

    api.orchestrator
      .run(projectId, ticketId)
      .then((result) => {
        setResults((prev) => new Map([...prev, [ticketId, result]]));
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`Pipeline error for ${ticketId}: ${msg}`);
      })
      .finally(() => {
        setRunning((prev) => {
          const next = new Set(prev);
          next.delete(ticketId);
          return next;
        });
      });
  }

  return { run, running, results };
}
