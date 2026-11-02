import { useEffect, useRef, useState } from "react";
import { useActiveProject } from "../useActiveProject";
import { useTickets } from "../useTickets";
import { useRuns } from "../useRuns";
import { useToast } from "../useToast";
import { useProjects } from "../useProjects";
import { useServices } from "../useServices";
import { useAppsEnCours } from "../useAppsEnCours";
import { useSupervision } from "../useSupervision";
import { useRunActif } from "../useRunActif";
import { parmi, useEtatPersistant } from "../useEtatPersistant";
import { useProjetMemorise } from "../useProjetMemorise";
import { useFiltresTickets } from "../useFiltresTickets";
import { useListeRuns } from "../runStore";
import { filtrerParStatut } from "../../lib/filtresTickets";
import { PANNEAUX } from "../../components/Sidebar/panels";
import type { SidebarPanel } from "../../components/Sidebar/panels";
import type { StatsPeriod } from "../../types/api";
import { vueDuCentre } from "../../vueDuCentre";

/**
 * Ce que les régions du cockpit se partagent — ticket-696 : l'état de la
 * vue, le projet actif, la socket de supervision et les listes lues par
 * plus d'une région. Chaque région en tire son groupe de props.
 *
 * ADR-013 tient toujours : pas de store, l'état reste dans ce hook et se
 * passe en argument aux hooks des régions.
 */
export function useCockpitNoyau() {
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
  // Le run regardé dans l'onglet Historique, à côté du ticket sélectionné
  // (ticket-427). Null : le plus récent du projet.
  const [runSelectionne, setRunSelectionne] = useState<string | null>(null);
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
  // Statuts lus depuis le store externe — ne redessine pas à chaque token
  // (ticket-354). `useListeRuns()` ne change de référence que si un statut
  // ou une pendingQuestion change.
  const runsStatus = useListeRuns();

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
  // Sans passer par `handleSelectProject` : la restauration ne doit pas écraser le panneau et la vue restaurés.
  const { memoriser } = useProjetMemorise(projets, project, setProject);
  const services = useServices(project?.id ?? null, supervision.signalServices);
  // Au niveau du cockpit : la pastille compte les apps même vue fermée (ticket-417).
  const appsEnCours = useAppsEnCours();
  const tickets = useTickets(project?.id ?? null, runEnCours, stream.events);
  const runs = useRuns(project?.id ?? null);
  // Une seule source de filtres pour la liste et le Kanban (ticket-195).
  const { filtres, setFiltres } = useFiltresTickets(project?.id ?? null);
  const filtrage = filtrerParStatut(tickets.tickets, filtres);

  // À la fin d'un pipeline : relire l'historique et dire l'issue.
  const prevLastResult = useRef(stream.lastResult);
  useEffect(() => {
    const fin = stream.lastResult;
    if (fin && fin !== prevLastResult.current) {
      prevLastResult.current = fin;
      runs.refresh();
      const tours = `${fin.rounds} tour${fin.rounds > 1 ? "s" : ""}`;
      if (fin.approved) addToast(`${fin.ticket_id} approuvé en ${tours}`, "success");
      else addToast(`${fin.ticket_id} bloqué après ${tours}`, "error");
    }
  });

  const running = new Set<string>(
    stream.ticketId && runEnCours ? [stream.ticketId] : [],
  );

  return {
    project, ticket, setProject, setTicket,
    panel, setPanel,
    showKanban, setShowKanban,
    runAuPremierPlan, setRunAuPremierPlan,
    openFilePath, setOpenFilePath,
    showDiff, setShowDiff,
    selection, setSelection,
    runSelectionne, setRunSelectionne,
    statsDays, setStatsDays,
    statsPortee, setStatsPortee,
    conversationId, setConversationChoisie,
    toasts, addToast, removeToast,
    supervision, stream, runsStatus, runEnCours, vueCentre,
    projets, memoriser, services, appsEnCours,
    tickets, runs, filtres, setFiltres, filtrage, running,
  };
}

export type CockpitNoyau = ReturnType<typeof useCockpitNoyau>;
