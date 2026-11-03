import { useMemo } from "react";
import { api } from "../lib/api";
import { criteresDuCorps } from "../lib/bureau/criteres";
import { useResource } from "./useResource";

const AUCUN: string[] = [];

/**
 * Les critères d'acceptation d'un ticket, lus dans son fichier (ticket-600) :
 * une seule lecture par ticket, sans minuterie — dix pièces ne doivent pas en
 * ouvrir dix. Sans projet ou sans ticket (`null`), rien n'est demandé.
 */
export function useCriteresDuTicket(projet: string | null, ticketId: string | null): string[] {
  const fetcher = useMemo(() => {
    if (projet === null || ticketId === null) return null;
    return async (): Promise<string[]> => {
      const { tickets } = await api.tickets.list(projet);
      const ticket = tickets.find((t) => t.id === ticketId);
      return ticket ? criteresDuCorps(ticket.body) : AUCUN;
    };
  }, [projet, ticketId]);
  return useResource(fetcher, AUCUN).data;
}
