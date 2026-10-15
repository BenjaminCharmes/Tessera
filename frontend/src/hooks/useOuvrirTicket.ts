import { createContext, useCallback, useContext, useEffect, useRef } from "react";
import { api } from "../lib/api";
import type { Project, Ticket } from "../types/api";

/** Outcome of opening a ticket: it never throws, the caller shows the message. */
export type ResultatOuverture = "ok" | "introuvable";

/** Opens a ticket's detail in the Tickets tab of its project (ticket-460). */
export type OuvrirTicket = (
  projectId: string,
  ticketId: string,
) => Promise<ResultatOuverture>;

/**
 * Sans fournisseur (un composant rendu seul, dans un test), l'action ne sait
 * rien ouvrir : elle le dit plutôt que de faire semblant.
 */
export const OuvrirTicketContext = createContext<OuvrirTicket>(
  async () => "introuvable",
);

/** The shared « open this ticket » action, as the cockpit provides it. */
export function useOuvrirTicket(): OuvrirTicket {
  return useContext(OuvrirTicketContext);
}

/** What the action needs from the cockpit: its state and its handlers. */
export interface PrisesDuCockpit {
  projets: Project[];
  projetActifId: string | null;
  selectionnerProjet: (projet: Project) => void;
  selectionnerTicket: (ticket: Ticket) => void;
  /** Passe sur l'onglet Tickets et ramène le centre devant le détail. */
  afficherLesTickets: () => void;
}

async function chercherLeTicket(
  projectId: string,
  ticketId: string,
): Promise<Ticket | null> {
  try {
    const { tickets } = await api.tickets.list(projectId);
    return tickets.find((t) => t.id === ticketId) ?? null;
  } catch {
    return null;
  }
}

/**
 * Builds the stable « open ticket » action — ticket-460.
 *
 * Le ticket est relu par l'API plutôt que cherché dans la liste du hook : après
 * un changement de projet, cette liste est celle de l'ancien projet jusqu'au
 * prochain chargement. Le projet n'est activé qu'une fois le ticket trouvé,
 * pour qu'un lien mort ne coûte pas le flux du projet courant.
 */
export function useActionOuvrirTicket(prises: PrisesDuCockpit): OuvrirTicket {
  const derniere = useRef(prises);
  useEffect(() => {
    derniere.current = prises;
  });

  return useCallback(async (projectId, ticketId) => {
    const projet = derniere.current.projets.find((p) => p.id === projectId);
    if (!projet) return "introuvable";
    const ticket = await chercherLeTicket(projectId, ticketId);
    if (!ticket) return "introuvable";

    const cockpit = derniere.current;
    // Changer de projet vide le ticket choisi : le ticket se pose après lui.
    if (cockpit.projetActifId !== projectId) cockpit.selectionnerProjet(projet);
    cockpit.selectionnerTicket(ticket);
    cockpit.afficherLesTickets();
    return "ok";
  }, []);
}
