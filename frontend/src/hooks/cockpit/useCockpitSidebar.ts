import type { Ticket } from "../../types/api";
import { demanderPermissionNotifications } from "../useNotificationsSysteme";
import { porteeEffectiveFor, prochainEtatKanban, runCachePour } from "./regles";
import type { CockpitActions } from "./useCockpitActions";
import type { CockpitAgent } from "./useCockpitAgent";
import type { CockpitNoyau } from "./useCockpitNoyau";

/**
 * Région de la colonne latérale — ticket-696 : les groupes de props que
 * `Sidebar` reçoit, un par panneau (projets, tickets, runs, usage, chat,
 * fichiers, agents).
 */
export function useCockpitSidebar(n: CockpitNoyau, a: CockpitActions, agent: CockpitAgent) {
  const { project, tickets, stream, vueCentre, filtrage } = n;
  const porteeEffective = porteeEffectiveFor(project, n.statsPortee);
  const agentsDesTickets = Array.from(
    new Set(tickets.tickets.map((t) => t.agent)),
  ).sort();

  return {
    projet: {
      actif: project,
      services: n.services,
      sortieDeService: n.supervision.sortieDuService,
      onSelect: a.handleSelectProject,
    },
    tickets: {
      byStatus: filtrage.byStatus,
      loading: tickets.loading,
      error: tickets.error,
      actif: n.ticket,
      running: n.running,
      runningRound: stream.currentRound,
      maxRounds: stream.maxRounds,
      // L'état actif du bouton se lit depuis la vue affichée, pas depuis
      // showKanban : quand le run est au premier plan avec showKanban=true,
      // le bouton ne doit pas paraître actif (ticket-287).
      showKanban: vueCentre === "kanban",
      runCache: runCachePour(n.runEnCours, vueCentre),
      filtres: n.filtres,
      total: filtrage.total,
      agents: agentsDesTickets,
      selection: n.selection,
      queueEnCours: n.runEnCours,
      onVoirLeRun: () => {
        n.setOpenFilePath(null);
        n.setShowDiff(false);
        n.setRunAuPremierPlan(true);
      },
      onSelect: a.handleSelectTicket,
      onSelectById: (ticketId: string) => {
        const found = tickets.tickets.find((t) => t.id === ticketId);
        if (found) {
          n.setTicket(found);
          n.setPanel("tickets");
        }
      },
      onRunPipeline: a.handleRunPipeline,
      onShowDiff: (ticketId: string) => {
        const found = tickets.tickets.find((t) => t.id === ticketId);
        if (found) n.setTicket(found);
        n.setOpenFilePath(null);
        n.setShowDiff(true);
      },
      onToggleQueue: a.handleToggleQueue,
      onRunQueue: a.handleRunQueue,
      onRunAutonome: (options: { depuisGithub: boolean }) => {
        n.setRunAuPremierPlan(true);
        void demanderPermissionNotifications();
        stream.connectAutonome(options);
      },
      onClearQueue: () => n.setSelection([]),
      onToggleKanban: () => {
        // Un fichier ouvert gardait la main sur le centre : basculer la vue
        // ne produisait rien tant qu'on ne l'avait pas refermé (ticket-073).
        // La décision part de la vue affichée, pas de showKanban : quand le
        // run occupait le premier plan avec showKanban=true, l'ancienne
        // logique (!v) passait showKanban à false et montrait l'éditeur
        // au lieu du tableau (ticket-287).
        n.setOpenFilePath(null);
        n.setShowDiff(false);
        n.setRunAuPremierPlan(false);
        n.setShowKanban(prochainEtatKanban(vueCentre));
      },
      onChangeFiltres: n.setFiltres,
      onCreated: (t: Ticket) => {
        tickets.refresh();
        n.setTicket(t);
        n.addToast(`Ticket « ${t.title} » créé`, "success");
      },
      onBatchCreated: (created: Ticket[]) => {
        tickets.refresh();
        const s = created.length !== 1 ? "s" : "";
        n.addToast(`${created.length} ticket${s} créé${s}`, "success");
      },
      onChangeStatus: a.handleChangeStatus,
    },
    runs: {
      liste: n.runs.runs,
      loading: n.runs.loading,
      error: n.runs.error,
      selectionne: n.runSelectionne,
      onSelect: n.setRunSelectionne,
    },
    usage: {
      days: n.statsDays,
      setDays: n.setStatsDays,
      portee: porteeEffective,
      setPortee: n.setStatsPortee,
      projetActifId: project?.id ?? null,
    },
    chat: {
      conversationId: n.conversationId,
      onSelect: (id: string) =>
        n.setConversationChoisie({ projet: project?.id ?? null, id }),
      onNew: () =>
        n.setConversationChoisie({
          projet: project?.id ?? null,
          id: `conv-${Date.now()}`,
        }),
    },
    fichiers: {
      ouvert: n.openFilePath,
      onOpen: a.handleOpenFile,
    },
    agents: agent,
  };
}
