import { useCallback } from "react";
import { api } from "../../lib/api";
import { noterRecent } from "../../lib/fichiersRecents";
import type { Project, Ticket, TicketStatus } from "../../types/api";
import { demanderPermissionNotifications } from "../useNotificationsSysteme";
import { ouvrirTicketsDuProjet, useActionOuvrirTicket } from "../useOuvrirTicket";
import { panelAfterProjectSwitch } from "./regles";
import type { CockpitNoyau } from "./useCockpitNoyau";

/**
 * Les gestes que plusieurs régions déclenchent — ticket-696 : choisir un
 * projet, un ticket ou un fichier, lancer un run, composer la file. Ils
 * lisent et écrivent l'état du noyau ; aucune région ne les redéfinit.
 */
export function useCockpitActions(n: CockpitNoyau) {
  const { project, projets, stream, setTicket, setOpenFilePath, setShowKanban } = n;

  function handleSelectProject(p: Project | null) {
    n.setProject(p);
    n.memoriser(p?.id ?? null);
    n.setPanel(panelAfterProjectSwitch(n.panel));
    // `showKanban` n'est pas touché : la vue du centre reste celle que l'utilisateur avait choisie
    // (ticket-425). Le fichier ouvert, lui, est celui de l'ancien projet : il se ferme.
    setOpenFilePath(null);
    stream.clear();
  }

  // Une notification ramène au projet concerné (ticket-192).
  const ouvrirProjet = useCallback(
    (id: string) => {
      const p = projets.find((x) => x.id === id);
      if (p) handleSelectProject(p);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [projets],
  );

  // Un fichier ouvert depuis l'arbre ou depuis la recherche : il est noté dans
  // les récents du projet, d'où « Ouverts récemment » (ticket-428).
  function handleOpenFile(path: string) {
    if (project) noterRecent(project.id, path);
    setOpenFilePath(path);
    setShowKanban(false);
  }

  // Le tableau est la vue *par défaut* ; choisir un ticket est explicite et
  // doit montrer ce ticket, sinon le clic ne produit rien de visible.
  function handleSelectTicket(t: Ticket) {
    setTicket(t);
    setOpenFilePath(null);
    setShowKanban(false);
    n.setShowDiff(false);
  }

  // Un numéro de ticket cliqué n'importe où ouvre son détail (ticket-460).
  // Le run en cours garde le centre tant qu'on ne le lui reprend pas.
  const ouvrirTicket = useActionOuvrirTicket({
    projets,
    projetActifId: project?.id ?? null,
    selectionnerProjet: handleSelectProject,
    selectionnerTicket: handleSelectTicket,
    afficherLesTickets: () => {
      n.setPanel("tickets");
      n.setRunAuPremierPlan(false);
    },
  });

  const ouvrirLesTicketsDuProjet = ouvrirTicketsDuProjet(handleSelectProject, n.setPanel); // porte du Bureau (ticket-602)

  // Un statut posé à la main (ticket-194) : le backend déplace le fichier et
  // publie l'événement ; on relit sans attendre le sondage.
  async function handleChangeStatus(ticketId: string, status: TicketStatus) {
    try {
      await api.tickets.setStatus(ticketId, status, project?.id ?? "");
      n.tickets.refresh();
    } catch (err: unknown) {
      n.addToast(err instanceof Error ? err.message : String(err), "error");
    }
  }

  // Lancer un run ramène sa vue devant : c'est le seul moment où l'IDE décide
  // à la place de l'utilisateur, et il vient précisément de le demander
  // (ticket-178).
  function handleRunPipeline(ticketId: string) {
    n.setRunAuPremierPlan(true);
    // La permission se demande au premier run lancé, jamais au chargement.
    void demanderPermissionNotifications();
    stream.connect(ticketId);
  }

  function handleToggleQueue(ticketId: string) {
    n.setSelection((prec) =>
      prec.includes(ticketId) ? prec.filter((t) => t !== ticketId) : [...prec, ticketId],
    );
  }

  function handleRunQueue() {
    n.setRunAuPremierPlan(true);
    void demanderPermissionNotifications();
    stream.connectQueue(n.selection);
  }

  return {
    handleSelectProject, ouvrirProjet, handleOpenFile, handleSelectTicket,
    ouvrirTicket, ouvrirLesTicketsDuProjet, handleChangeStatus,
    handleRunPipeline, handleToggleQueue, handleRunQueue,
  };
}

export type CockpitActions = ReturnType<typeof useCockpitActions>;
