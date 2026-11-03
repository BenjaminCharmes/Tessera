import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { usePolling } from "./usePolling";
import type { PRStatus, Ticket } from "../types/api";

const POLL_INTERVAL_MS = 30_000;

/**
 * Clé des PR connues d'une liste de tickets : elle change quand un run ouvre
 * une nouvelle PR, ce qui relance le chargement (ticket-367).
 */
export function clePrDesTickets(tickets: readonly Ticket[]): string {
  return tickets
    .filter((t) => t.pr_number)
    .map((t) => `${t.id}:${t.pr_number}`)
    .sort()
    .join(",");
}

/**
 * Charge l'état de toutes les PR d'un projet en une seule requête et le rend
 * sous forme de table `ticket_id → PRStatus` (ticket-367).
 *
 * - Ne démarre que si `projectId` est fourni, la fenêtre visible, et sauf si
 *   `clePr` dit qu'aucun ticket ne porte de PR (chaîne vide).
 * - Renouvelle toutes les 30 s tant qu'au moins une PR est `open`.
 * - S'arrête quand toutes les PR sont réglées, jusqu'à ce que `clePr` change :
 *   une PR ouverte par un run relance le chargement.
 * - Une erreur 4xx (projet sans dépôt GitHub, jeton absent) ne changera pas au
 *   prochain essai : le polling s'arrête (ticket-217). Une 5xx réessaie.
 * - Suspend le polling quand la fenêtre est cachée ; reprend au retour.
 */
export function usePrStatuses(
  projectId: string | null,
  clePr?: string,
): Record<string, PRStatus> {
  // La table est rangée avec le projet qui l'a produite : celle d'un autre
  // projet ne s'affiche jamais, les identifiants de tickets s'y recoupent.
  const [charge, setCharge] = useState<{
    projet: string;
    table: Record<string, PRStatus>;
  } | null>(null);

  // Toutes les PR sont réglées (ou la requête ne peut plus aboutir) : plus
  // rien à demander tant que le projet ou `clePr` ne change pas.
  const cle = `${projectId ?? ""}|${clePr ?? "?"}`;
  const [reglee, setReglee] = useState(false);
  const [cleVue, setCleVue] = useState(cle);
  if (cleVue !== cle) {
    setCleVue(cle);
    setReglee(false);
  }
  const cleCourante = useRef(cle);
  useEffect(() => {
    cleCourante.current = cle;
  }, [cle]);

  const lire = useCallback(async () => {
    if (!projectId) return;
    try {
      const entries = await api.github.getPrStatuses(projectId);
      if (cleCourante.current !== cle) return;
      const table: Record<string, PRStatus> = {};
      for (const e of entries) {
        table[e.ticket_id] = {
          state: e.state,
          ci_status: e.ci_status,
          pr_url: e.pr_url,
          pr_number: e.pr_number,
        };
      }
      setCharge({ projet: projectId, table });
      if (!entries.some((e) => e.state === "open")) setReglee(true);
    } catch (err) {
      if (cleCourante.current !== cle) return;
      if (err instanceof Error && /^API 4\d\d\b/.test(err.message)) setReglee(true);
    }
  }, [projectId, cle]);

  // `clePr` vide : aucun ticket ne porte de PR, rien à demander.
  const actif = projectId !== null && clePr !== "" && !reglee;
  usePolling(lire, {
    cadenceMs: actif ? POLL_INTERVAL_MS : null,
    immediat: true,
    relance: cle,
  });

  return charge !== null && charge.projet === projectId ? charge.table : VIDE;
}

const VIDE: Record<string, PRStatus> = {};
