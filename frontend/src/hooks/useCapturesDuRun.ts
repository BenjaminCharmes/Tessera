import { useMemo } from "react";
import { listerLesCaptures } from "../lib/capturesDuRun";
import { useResource } from "./useResource";

const AUCUNE: string[] = [];

/**
 * Les noms des images qu'un run a prises (ticket-620). Sans projet, rien n'est
 * demandé ; une erreur de lecture se comporte comme « rien capturé » : la section
 * ne s'affiche pas plutôt que d'annoncer une panne dans un écran d'historique.
 */
export function useCapturesDuRun(projet: string | null, ticketId: string): string[] {
  const fetcher = useMemo(
    () => (projet === null ? null : () => listerLesCaptures(projet, ticketId)),
    [projet, ticketId],
  );
  return useResource(fetcher, AUCUNE).data;
}
