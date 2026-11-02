import type { Project } from "../../types/api";
import { FILTRES_VIDES } from "../../lib/filtresTickets";
import { projetsEnAttente } from "../../components/Sidebar/projetsEnAttente";
import { porteeEffectiveFor } from "./regles";
import type { CockpitActions } from "./useCockpitActions";
import type { CockpitAgent } from "./useCockpitAgent";
import type { CockpitNoyau } from "./useCockpitNoyau";
import type { useCockpitNotifications } from "./useCockpitNotifications";

type Son = ReturnType<typeof useCockpitNotifications>["son"];

/**
 * Région du centre — ticket-696 : le groupe de props de `CenterView` (vue
 * affichée, Bureau, historique, kanban, statistiques, file de run).
 */
export function useCockpitCentre(
  n: CockpitNoyau,
  a: CockpitActions,
  agent: CockpitAgent,
  son: Son,
) {
  const { project, tickets, runs, filtrage, supervision } = n;
  const porteeEffective = porteeEffectiveFor(project, n.statsPortee);
  // Une question ne se voyait que dans le panneau du projet sélectionné : la
  // sidebar la signale depuis n'importe quel onglet (ticket-186).
  const enAttente = projetsEnAttente(
    supervision.runs,
    (runId) => n.runsStatus.find((r) => r.runId === runId)?.pendingQuestion ?? null,
  );

  return {
    vueCentre: n.vueCentre,
    project,
    projets: n.projets,
    ticket: n.ticket,
    conversationId: n.conversationId,
    supervision,
    son,
    servicesDuProjet: n.services.services,
    appsEnCours: n.appsEnCours,
    agentSelectionne: agent.selectionne,
    onSelectAgent: agent.onSelect,
    historique: {
      runs: runs.runs,
      loading: runs.loading,
      error: runs.error,
      runSelectionne: n.runSelectionne,
      onSelectRun: n.setRunSelectionne,
      tickets: tickets.tickets,
    },
    stream: n.stream,
    byStatus: filtrage.byStatus,
    filtres: n.filtres,
    total: filtrage.total,
    retenus: filtrage.retenus,
    onClearFiltres: () => n.setFiltres(FILTRES_VIDES),
    running: n.running,
    unreadable: tickets.unreadable,
    openFilePath: n.openFilePath,
    onOpenFile: a.handleOpenFile,
    onCloseFile: () => n.setOpenFilePath(null),
    statsDays: n.statsDays,
    // La portée effective est "tous" quand aucun projet n'est actif.
    statsProjectId: porteeEffective === "tous" ? null : (project?.id ?? null),
    onSelectProject: a.handleSelectProject,
    onOpenProject: a.ouvrirLesTicketsDuProjet,
    enAttente,
    onProjectCreated: (p: Project) => n.addToast(`Projet « ${p.name} » créé`, "success"),
    onSelectTicket: a.handleSelectTicket,
    onRunPipeline: a.handleRunPipeline,
    onChangeStatus: a.handleChangeStatus,
    selection: n.selection,
    queueEnCours: n.runEnCours,
    onToggleQueue: a.handleToggleQueue,
    onRunQueue: a.handleRunQueue,
    onClearQueue: () => n.setSelection([]),
  };
}
