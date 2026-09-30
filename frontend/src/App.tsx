import { useCallback, useEffect, useRef } from "react";
import { useState } from "react";
import { useActiveProject } from "./hooks/useActiveProject";
import { useTickets } from "./hooks/useTickets";
import { useRuns } from "./hooks/useRuns";
import { useUsage } from "./hooks/useUsage";
import { useToast } from "./hooks/useToast";
import { useProjects } from "./hooks/useProjects";
import { useServices } from "./hooks/useServices";
import { useSupervision } from "./hooks/useSupervision";
import { useRunActif } from "./hooks/useRunActif";
import { parmi, useEtatPersistant } from "./hooks/useEtatPersistant";
import { useProjetMemorise } from "./hooks/useProjetMemorise";
import { useFiltresTickets } from "./hooks/useFiltresTickets";
import {
  demanderPermissionNotifications,
  useNotificationsSysteme,
} from "./hooks/useNotificationsSysteme";
import { filtrerParStatut } from "./lib/filtresTickets";
import { PANNEAUX } from "./components/Sidebar/panels";
import Sidebar from "./components/Sidebar";
import NavRail from "./components/Sidebar/NavRail";
import type { SidebarPanel } from "./components/Sidebar";
import DiffView from "./components/DiffView";
import AgentDetail from "./components/AgentDetail";
import StatsView from "./components/StatsView";
import SupervisionView from "./components/SupervisionView";
import RunView from "./components/RunView";
import Editor from "./components/Editor";
import KanbanView from "./components/KanbanView";
import ChatPanel from "./components/ChatPanel";
import BottomPanel from "./components/BottomPanel";
import ErrorBoundary from "./components/ErrorBoundary";
import ToastContainer from "./components/Toast";
import type { Project, Ticket, TicketStatus } from "./types/api";
import { api } from "./lib/api";
import { vueDuCentre } from "./vueDuCentre";
import { projetsEnAttente } from "./components/Sidebar/projetsEnAttente";

export default function App() {
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
  // tout geste explicite le lui reprend. Sans cet état, « Vue liste » n'avait
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
  // regarde — pour les composants qui n'en attendaient qu'un.
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
  const notifications = useNotificationsSysteme(supervision, project?.id ?? null, ouvrirProjet);
  const services = useServices(project?.id ?? null, supervision.signalServices);

  // Ce que la pastille doit dire avant tout le reste : un agent qui attend
  // bloque un humain, un run bloqué demande une décision. L'activité est le
  // cas nominal, donc le dernier à mériter la couleur.
  const etatsDesRuns = supervision.runs.map((r) =>
    supervision.etatDe(r.run_id),
  );
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
  const agentsDesTickets = Array.from(new Set(tickets.tickets.map((t) => t.agent))).sort();
  const usageData = useUsage(project?.id ?? null);

  // Refresh run history and show toast when a pipeline completes
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

  function handleSelectProject(p: typeof project) {
    setProject(p);
    memoriser(p?.id ?? null);
    setPanel("tickets");
    setShowKanban(true);
    setOpenFilePath(null);
    stream.clear();
  }

  function handleProjectCreated(p: Project) {
    addToast(`Projet « ${p.name} » créé`, "success");
  }

  // Le tableau est la vue *par défaut* ; choisir un ticket est explicite et
  // doit montrer ce ticket, sinon le clic ne produit rien de visible.
  function handleSelectTicket(t: Ticket) {
    setTicket(t);
    setOpenFilePath(null);
    setShowKanban(false);
    setShowDiff(false);
  }

  function handleTicketCreated(t: Ticket) {
    tickets.refresh();
    setTicket(t);
    addToast(`Ticket « ${t.title} » créé`, "success");
  }

  // Le ticket porte désormais un `pr_number` : la liste se relit pour le
  // montrer. `TicketCard` attendait ce rappel sans que rien ne le fournisse
  // (ticket-123).
  // Un statut posé à la main (ticket-194) : le backend déplace le fichier
  // et publie l'événement ; on relit la liste sans attendre le sondage.
  async function handleChangeStatus(ticketId: string, status: TicketStatus) {
    try {
      await api.tickets.setStatus(ticketId, status, project?.id ?? "");
      tickets.refresh();
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : String(err), "error");
    }
  }

  function handleBatchCreated(created: Ticket[]) {
    tickets.refresh();
    addToast(
      `${created.length} ticket${created.length !== 1 ? "s" : ""} créé${created.length !== 1 ? "s" : ""}`,
      "success",
    );
  }

  // Lancer un run ramène sa vue devant : c'est le seul moment où l'IDE décide
  // à la place de l'utilisateur, et il vient précisément de le demander. Le
  // décider ici plutôt qu'en observant `status` évite un `setState` dans un
  // effet, et dit mieux ce qui se passe (ticket-178).
  function handleRunPipeline(ticketId: string) {
    setRunAuPremierPlan(true);
    // La permission se demande au premier run lancé, jamais au chargement.
    void demanderPermissionNotifications();
    stream.connect(ticketId);
  }

  function handleAgentCreated(role: string) {
    addToast(`Agent \`${role}\` créé`, "success");
  }

  function handleSelectTicketById(ticketId: string) {
    const found = tickets.tickets.find((t) => t.id === ticketId);
    if (found) {
      setTicket(found);
      setPanel("tickets");
    }
  }

  return (
    <div
      className="h-screen overflow-hidden bg-zinc-900 text-zinc-100"
      style={{
        display: "grid",
        gridTemplateColumns: "100px 280px 1fr",
        gridTemplateRows: "1fr 180px",
      }}
    >
      {/* Icon bar — col 1, rows 1-2 */}
      <div
        className="border-r border-zinc-700"
        style={{ gridColumn: "1", gridRow: "1 / 3" }}
      >
        <NavRail
          activePanel={panel}
          onChangePanel={setPanel}
          runsActifs={supervision.runs.length}
          alerte={alerteDeSupervision}
        />
      </div>

      {/* Sidebar — col 2, rows 1-2.
          Nommée : depuis que le tableau des tickets occupe le centre, les
          mêmes titres apparaissent des deux côtés. Une assertion qui ne dit
          pas de quelle région elle parle en trouve deux. */}
      <aside
        aria-label="Panneau latéral"
        className="border-r border-zinc-700 overflow-hidden"
        style={{ gridColumn: "2", gridRow: "1 / 3" }}
      >
        <ErrorBoundary>
          <Sidebar
            panel={panel}
            projetsEnAttente={enAttente}
            services={services}
            sortieDeService={supervision.sortieDuService}
            activeProject={project}
            activeTicket={ticket}
            byStatus={filtrage.byStatus}
            filtres={filtres}
            onChangeFiltres={setFiltres}
            totalTickets={filtrage.total}
            agentsDesTickets={agentsDesTickets}
            ticketsLoading={tickets.loading}
            ticketsError={tickets.error}
            runs={runs.runs}
            runsLoading={runs.loading}
            runsError={runs.error}
            usage={usageData.usage}
            usageLoading={usageData.loading}
            usageError={usageData.error}
            chatConversationId={conversationId}
            onSelectConversation={(id) =>
              setConversationChoisie({ projet: project?.id ?? null, id })
            }
            onNewConversation={() =>
              setConversationChoisie({
                projet: project?.id ?? null,
                id: `conv-${Date.now()}`,
              })
            }
            running={running}
            runningRound={stream.currentRound}
            maxRounds={stream.maxRounds}
            showKanban={showKanban}
            runCache={runEnCours && !runAuPremierPlan}
            onVoirLeRun={() => {
              setOpenFilePath(null);
              setShowDiff(false);
              setRunAuPremierPlan(true);
            }}
            onSelectProject={handleSelectProject}
            onChangeStatus={handleChangeStatus}
            notifications={{
              active: notifications.active,
              etat: notifications.etat,
              onChange: notifications.setActive,
            }}
            onProjectCreated={handleProjectCreated}
            onSelectTicket={handleSelectTicket}
            onRunPipeline={handleRunPipeline}
            onShowDiff={(ticketId) => {
              const found = tickets.tickets.find((t) => t.id === ticketId);
              if (found) setTicket(found);
              setOpenFilePath(null);
              setShowDiff(true);
            }}
            onToggleKanban={() => {
              // Un fichier ouvert gardait la main sur le centre : basculer la
              // vue ne produisait rien tant qu'on ne l'avait pas refermé
              // (ticket-073).
              setOpenFilePath(null);
              setShowDiff(false);
              setRunAuPremierPlan(false);
              setShowKanban((v) => !v);
            }}
            onTicketCreated={handleTicketCreated}
            onBatchCreated={handleBatchCreated}
            onSelectTicketById={handleSelectTicketById}
            onAgentCreated={handleAgentCreated}
            agentSelectionne={agentSelectionne}
            onSelectAgent={setAgentSelectionne}
            selection={selection}
            queueEnCours={
              stream.status === "running" || stream.status === "connecting"
            }
            onToggleQueue={(ticketId) =>
              setSelection((prec) =>
                prec.includes(ticketId)
                  ? prec.filter((t) => t !== ticketId)
                  : [...prec, ticketId],
              )
            }
            onRunQueue={() => {
              setRunAuPremierPlan(true);
              void demanderPermissionNotifications();
              stream.connectQueue(selection);
            }}
            onRunAutonome={(options) => {
              setRunAuPremierPlan(true);
              void demanderPermissionNotifications();
              stream.connectAutonome(options);
            }}
            onClearQueue={() => setSelection([])}
            openFilePath={openFilePath}
            onOpenFile={(path) => {
              setOpenFilePath(path);
              setShowKanban(false);
            }}
          />
        </ErrorBoundary>
      </aside>

      {/* Center — col 3, row 1 : le tableau des tickets, ou un fichier en
          lecture seule quand on en a ouvert un (ticket-065). */}
      <main
        aria-label="Vue principale"
        className="overflow-hidden"
        style={{ gridColumn: "3", gridRow: "1" }}
      >
        <ErrorBoundary>
          {/* L'onglet Agents donne enfin un détail au centre : le rail dit
           *quel* agent, le centre montre *ce qu'il est* (ticket-076). */}
          {/* Pendant un run, le centre montre le run. C'est le moment où l'on
              a le plus besoin de place, et où il en occupait le moins : le
              tableau des tickets, ou « ce ticket n'a jamais été lancé »
              (ticket-075). Un fichier ou un diff ouvert explicitement garde la
              priorité : c'est une demande de l'utilisateur. */}
          {panel === "chat" ? (
            // Le chat a sa propre vue centrale : plus large que l'ancienne
            // colonne de droite, et sans partager la place avec les agents
            // (ticket-223).
            <ChatPanel project={project} conversationId={conversationId} />
          ) : panel === "supervision" ? (
            // Vue globale : elle ne dépend d'aucun projet actif, comme les
            // coûts. C'est ce qui lui permet de montrer les autres.
            <SupervisionView
              supervision={supervision}
              projects={projets}
              services={services.services}
            />
          ) : panel === "agents" ? (
            <AgentDetail
              role={agentSelectionne}
              projectId={project?.id ?? null}
            />
          ) : panel === "usage" ? (
            // Sans projet sélectionné, la vue d'ensemble : « combien me coûte
            // Tessera, et sur quel projet » n'avait aucune réponse.
            <StatsView projectId={project?.id ?? null} />
          ) : vueCentre === "run" ? (
            <RunView stream={stream} />
          ) : vueCentre === "diff" && project && ticket ? (
            <DiffView projectId={project.id} ticketId={ticket.id} />
          ) : vueCentre === "kanban" ? (
            <KanbanView
              byStatus={filtrage.byStatus}
              activeTicket={ticket}
              running={running}
              githubRemote={project?.github_remote ?? null}
              projectId={project?.id ?? null}
              unreadable={tickets.unreadable}
              onSelectTicket={handleSelectTicket}
              onRunPipeline={handleRunPipeline}
              onChangeStatus={handleChangeStatus}
            />
          ) : (
            <Editor ticket={ticket} openFilePath={openFilePath} />
          )}
        </ErrorBoundary>
      </main>

      {/* Bottom Panel — col 3, row 2 */}
      <div
        className="overflow-hidden"
        style={{ gridColumn: "3", gridRow: "2" }}
      >
        <BottomPanel events={stream.events} />
      </div>

      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </div>
  );
}
