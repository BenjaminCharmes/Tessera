import { useCallback, useEffect, useRef, useState } from "react";
import { useActiveProject } from "./useActiveProject";
import { useTickets } from "./useTickets";
import { useRuns } from "./useRuns";
import { useUsage } from "./useUsage";
import { useToast } from "./useToast";
import { useProjects } from "./useProjects";
import { useServices } from "./useServices";
import { useSupervision } from "./useSupervision";
import { useRunActif } from "./useRunActif";
import { parmi, useEtatPersistant } from "./useEtatPersistant";
import { useProjetMemorise } from "./useProjetMemorise";
import { useFiltresTickets } from "./useFiltresTickets";
import {
  demanderPermissionNotifications,
  useNotificationsSysteme,
} from "./useNotificationsSysteme";
import { filtrerParStatut } from "../lib/filtresTickets";
import { PANNEAUX } from "../components/Sidebar/panels";
import type { SidebarPanel } from "../components/Sidebar/panels";
import { projetsEnAttente } from "../components/Sidebar/projetsEnAttente";
import type { Project, StatsPeriod, Ticket, TicketStatus } from "../types/api";
import { api } from "../lib/api";
import { vueDuCentre } from "../vueDuCentre";

/**
 * Returns the panel to activate when the user selects a project from the
 * selector. Coming from the projects list always opens tickets; any other
 * panel stays — the user was already where they wanted to be (ticket-271).
 */
export function panelAfterProjectSwitch(
  current: SidebarPanel,
): SidebarPanel {
  return current === "projects" ? "tickets" : current;
}

/**
 * The cockpit's state graph — ticket-252.
 *
 * App.tsx portait tout : l'état, les hooks, les gestionnaires, et une
 * cinquantaine de props passées à plat vers la colonne latérale. Ce hook
 * assemble le graphe et rend des groupes prêts à poser sur chaque région —
 * App ne fait plus que composer la grille.
 *
 * ADR-013 tient toujours : pas de store. Si les groupes ne suffisent plus,
 * la réévaluation (Zustand) mérite son propre ADR, pas un glissement.
 */
export function useCockpit() {
  const { project, ticket, setProject, setTicket } = useActiveProject();
  // Le panneau, la vue et l'onglet de droite survivent au rechargement
  // (ticket-193) ; le projet actif aussi, via `useProjetMemorise` plus bas.
  const [panel, setPanel] = useEtatPersistant<SidebarPanel>(
    "panneau",
    "projects",
    parmi(PANNEAUX),
  );
  // Le centre montre le tableau des tickets par défaut, pas un fichier : le
  // cockpit sert à suivre la flotte, et l'édition est partie dans VSCode
  // (ticket-065).
  const [showKanban, setShowKanban] = useEtatPersistant<boolean>(
    "kanban",
    true,
    (v): v is boolean => typeof v === "boolean",
  );
  // Le run passe devant quand il démarre — c'est ce qu'on veut voir — mais
  // tout geste explicite le lui reprend. Sans cet état, « Éditeur » n'avait
  // aucun effet tant qu'un run tournait (ticket-178).
  const [runAuPremierPlan, setRunAuPremierPlan] = useState(true);
  const [openFilePath, setOpenFilePath] = useState<string | null>(null);
  // Relire ce qu'un run a produit sans quitter l'IDE (ticket-069).
  const [showDiff, setShowDiff] = useState(false);

  // L'ordre de la file est celui de la sélection, pas celui de la liste : un
  // lot du planificateur a des dépendances, et c'est à l'utilisateur de les
  // ordonner (ticket-074).
  const [selection, setSelection] = useState<string[]>([]);
  const [agentSelectionne, setAgentSelectionne] = useState<string | null>(null);
  // La période et la portée des statistiques vivent ici pour que la colonne
  // latérale les contrôle et que StatsView les reçoive en props (ticket-253).
  const [statsDays, setStatsDays] = useState<StatsPeriod>(30);
  const [statsPortee, setStatsPortee] = useState<"projet" | "tous">("projet");

  // La liste des conversations vit dans la colonne 2, le fil au centre
  // (ticket-250) : l'état est donc partagé ici. Le choix retient son projet —
  // en changer retombe sur `default` sans effet ni rendu en cascade.
  const [conversationChoisie, setConversationChoisie] = useState<{
    projet: string | null;
    id: string;
  }>({ projet: null, id: "default" });
  const conversationId =
    conversationChoisie.projet === (project?.id ?? null)
      ? conversationChoisie.id
      : "default";
  const { toasts, addToast, removeToast } = useToast();

  // Une seule socket pour toute la machine (ticket-129) : `supervision`
  // porte tous les runs, `stream` n'en projette qu'un — celui du projet
  // regardé — pour les composants qui n'en attendaient qu'un.
  const supervision = useSupervision();
  const stream = useRunActif(supervision, project?.id ?? null);
  // Une question ne se voyait que dans le panneau du projet sélectionné : la
  // sidebar la signale depuis n'importe quel onglet (ticket-186).
  const enAttente = projetsEnAttente(
    supervision.runs,
    (runId) => supervision.etatDe(runId).pendingQuestion,
  );

  const runEnCours =
    stream.status === "running" || stream.status === "connecting";
  const vueCentre = vueDuCentre({
    runEnCours,
    runAuPremierPlan,
    openFilePath,
    showDiff,
    showKanban,
  });
  const { projects: projets } = useProjects();
  // Sans passer par `handleSelectProject` : la restauration ne doit pas
  // écraser le panneau et la vue, eux aussi restaurés.
  const { memoriser } = useProjetMemorise(projets, project, setProject);
  // Une notification ramène au projet concerné (ticket-192).
  const ouvrirProjet = useCallback(
    (id: string) => {
      const p = projets.find((x) => x.id === id);
      if (p) handleSelectProject(p);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [projets],
  );
  const notifications = useNotificationsSysteme(
    supervision,
    project?.id ?? null,
    ouvrirProjet,
  );
  const services = useServices(project?.id ?? null, supervision.signalServices);

  // Ce que la pastille doit dire avant tout le reste : un agent qui attend
  // bloque un humain, un run bloqué demande une décision. L'activité est le
  // cas nominal, donc le dernier à mériter la couleur.
  const etatsDesRuns = supervision.runs.map((r) => supervision.etatDe(r.run_id));
  const alerteDeSupervision = etatsDesRuns.some((e) => e.status === "error")
    ? ("bloque" as const)
    : etatsDesRuns.some((e) => e.pendingQuestion !== null)
      ? ("attente" as const)
      : null;
  const tickets = useTickets(
    project?.id ?? null,
    stream.status === "running" || stream.status === "connecting",
    stream.events,
  );
  const runs = useRuns(project?.id ?? null);
  // Une seule source de filtres pour la liste et le Kanban (ticket-195).
  const { filtres, setFiltres } = useFiltresTickets(project?.id ?? null);
  const filtrage = filtrerParStatut(tickets.tickets, filtres);
  const agentsDesTickets = Array.from(
    new Set(tickets.tickets.map((t) => t.agent)),
  ).sort();
  const usageData = useUsage(project?.id ?? null);

  // À la fin d'un pipeline : relire l'historique et le coût, dire l'issue.
  const prevLastResult = useRef(stream.lastResult);
  useEffect(() => {
    if (stream.lastResult && stream.lastResult !== prevLastResult.current) {
      prevLastResult.current = stream.lastResult;
      runs.refresh();
      usageData.refresh();
      if (stream.lastResult.approved) {
        addToast(
          `${stream.lastResult.ticket_id} approuvé en ${stream.lastResult.rounds} tour${stream.lastResult.rounds > 1 ? "s" : ""}`,
          "success",
        );
      } else {
        addToast(
          `${stream.lastResult.ticket_id} bloqué après ${stream.lastResult.rounds} tour${stream.lastResult.rounds > 1 ? "s" : ""}`,
          "error",
        );
      }
    }
  });

  const running = new Set<string>(
    stream.ticketId &&
      (stream.status === "running" || stream.status === "connecting")
      ? [stream.ticketId]
      : [],
  );

  function handleSelectProject(p: Project | null) {
    setProject(p);
    memoriser(p?.id ?? null);
    setPanel(panelAfterProjectSwitch(panel));
    setShowKanban(true);
    setOpenFilePath(null);
    stream.clear();
  }

  // Le tableau est la vue *par défaut* ; choisir un ticket est explicite et
  // doit montrer ce ticket, sinon le clic ne produit rien de visible.
  function handleSelectTicket(t: Ticket) {
    setTicket(t);
    setOpenFilePath(null);
    setShowKanban(false);
    setShowDiff(false);
  }

  // Le ticket porte un `pr_number` : la liste se relit pour le montrer
  // (ticket-123). Un statut posé à la main (ticket-194) : le backend déplace
  // le fichier et publie l'événement ; on relit sans attendre le sondage.
  async function handleChangeStatus(ticketId: string, status: TicketStatus) {
    try {
      await api.tickets.setStatus(ticketId, status, project?.id ?? "");
      tickets.refresh();
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : String(err), "error");
    }
  }

  // Lancer un run ramène sa vue devant : c'est le seul moment où l'IDE décide
  // à la place de l'utilisateur, et il vient précisément de le demander
  // (ticket-178).
  function handleRunPipeline(ticketId: string) {
    setRunAuPremierPlan(true);
    // La permission se demande au premier run lancé, jamais au chargement.
    void demanderPermissionNotifications();
    stream.connect(ticketId);
  }

  return {
    panel,
    setPanel,
    navRail: {
      runsActifs: supervision.runs.length,
      alerte: alerteDeSupervision,
    },
    sidebar: {
      projet: {
        actif: project,
        enAttente,
        services,
        sortieDeService: supervision.sortieDuService,
        notifications: {
          active: notifications.active,
          etat: notifications.etat,
          onChange: notifications.setActive,
        },
        onSelect: handleSelectProject,
        onCreated: (p: Project) => addToast(`Projet « ${p.name} » créé`, "success"),
      },
      tickets: {
        byStatus: filtrage.byStatus,
        loading: tickets.loading,
        error: tickets.error,
        actif: ticket,
        running,
        runningRound: stream.currentRound,
        maxRounds: stream.maxRounds,
        showKanban,
        runCache: runEnCours && !runAuPremierPlan,
        filtres,
        total: filtrage.total,
        agents: agentsDesTickets,
        selection,
        queueEnCours: runEnCours,
        onVoirLeRun: () => {
          setOpenFilePath(null);
          setShowDiff(false);
          setRunAuPremierPlan(true);
        },
        onSelect: handleSelectTicket,
        onSelectById: (ticketId: string) => {
          const found = tickets.tickets.find((t) => t.id === ticketId);
          if (found) {
            setTicket(found);
            setPanel("tickets");
          }
        },
        onRunPipeline: handleRunPipeline,
        onShowDiff: (ticketId: string) => {
          const found = tickets.tickets.find((t) => t.id === ticketId);
          if (found) setTicket(found);
          setOpenFilePath(null);
          setShowDiff(true);
        },
        onToggleQueue: (ticketId: string) =>
          setSelection((prec) =>
            prec.includes(ticketId)
              ? prec.filter((t) => t !== ticketId)
              : [...prec, ticketId],
          ),
        onRunQueue: () => {
          setRunAuPremierPlan(true);
          void demanderPermissionNotifications();
          stream.connectQueue(selection);
        },
        onRunAutonome: (options: { depuisGithub: boolean }) => {
          setRunAuPremierPlan(true);
          void demanderPermissionNotifications();
          stream.connectAutonome(options);
        },
        onClearQueue: () => setSelection([]),
        onToggleKanban: () => {
          // Un fichier ouvert gardait la main sur le centre : basculer la vue
          // ne produisait rien tant qu'on ne l'avait pas refermé (ticket-073).
          setOpenFilePath(null);
          setShowDiff(false);
          setRunAuPremierPlan(false);
          setShowKanban((v) => !v);
        },
        onChangeFiltres: setFiltres,
        onCreated: (t: Ticket) => {
          tickets.refresh();
          setTicket(t);
          addToast(`Ticket « ${t.title} » créé`, "success");
        },
        onBatchCreated: (created: Ticket[]) => {
          tickets.refresh();
          addToast(
            `${created.length} ticket${created.length !== 1 ? "s" : ""} créé${created.length !== 1 ? "s" : ""}`,
            "success",
          );
        },
        onChangeStatus: handleChangeStatus,
      },
      runs: { liste: runs.runs, loading: runs.loading, error: runs.error },
      usage: {
        usage: usageData.usage,
        loading: usageData.loading,
        error: usageData.error,
        days: statsDays,
        setDays: setStatsDays,
        portee: statsPortee,
        setPortee: setStatsPortee,
        projetActifId: project?.id ?? null,
      },
      chat: {
        conversationId,
        onSelect: (id: string) =>
          setConversationChoisie({ projet: project?.id ?? null, id }),
        onNew: () =>
          setConversationChoisie({
            projet: project?.id ?? null,
            id: `conv-${Date.now()}`,
          }),
      },
      fichiers: {
        ouvert: openFilePath,
        onOpen: (path: string) => {
          setOpenFilePath(path);
          setShowKanban(false);
        },
      },
      agents: {
        selectionne: agentSelectionne,
        onSelect: setAgentSelectionne,
        onCreated: (role: string) => addToast(`Agent \`${role}\` créé`, "success"),
      },
    },
    centre: {
      vueCentre,
      project,
      projets,
      ticket,
      conversationId,
      supervision,
      servicesDuProjet: services.services,
      agentSelectionne,
      stream,
      byStatus: filtrage.byStatus,
      running,
      unreadable: tickets.unreadable,
      openFilePath,
      statsDays,
      // Quand la portée est "tous", on passe null même si un projet est actif.
      statsProjectId: statsPortee === "tous" ? null : (project?.id ?? null),
      onSelectTicket: handleSelectTicket,
      onRunPipeline: handleRunPipeline,
      onChangeStatus: handleChangeStatus,
    },
    events: stream.events,
    toasts,
    fermerToast: removeToast,
  };
}
