import { useEffect, useRef } from "react";
import { useState } from "react";
import { useActiveProject } from "./hooks/useActiveProject";
import { useTickets } from "./hooks/useTickets";
import { useRuns } from "./hooks/useRuns";
import { useUsage } from "./hooks/useUsage";
import { useToast } from "./hooks/useToast";
import { useOrchestratorStream } from "./hooks/useOrchestratorStream";
import Sidebar, { IconBar } from "./components/Sidebar";
import type { SidebarPanel } from "./components/Sidebar";
import Editor from "./components/Editor";
import KanbanView from "./components/KanbanView";
import AgentPanel from "./components/AgentPanel";
import BottomPanel from "./components/BottomPanel";
import ErrorBoundary from "./components/ErrorBoundary";
import ToastContainer from "./components/Toast";
import type { Project, Ticket } from "./types/api";

export default function App() {
  const { project, ticket, setProject, setTicket } = useActiveProject();
  const [panel, setPanel] = useState<SidebarPanel>("projects");
  const [showKanban, setShowKanban] = useState(false);
  const { toasts, addToast, removeToast } = useToast();

  const stream = useOrchestratorStream(project?.id ?? null);
  const tickets = useTickets(
    project?.id ?? null,
    stream.status === "running" || stream.status === "connecting",
    stream.events,
  );
  const runs = useRuns(project?.id ?? null);
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
    setPanel("tickets");
    setShowKanban(false);
    stream.clear();
  }

  function handleProjectCreated(p: Project) {
    addToast(`Projet « ${p.name} » créé`, "success");
  }

  function handleTicketCreated(t: Ticket) {
    tickets.refresh();
    setTicket(t);
    addToast(`Ticket « ${t.title} » créé`, "success");
  }

  function handleBatchCreated(created: Ticket[]) {
    tickets.refresh();
    addToast(
      `${created.length} ticket${created.length !== 1 ? "s" : ""} créé${created.length !== 1 ? "s" : ""}`,
      "success",
    );
  }

  function handleRunPipeline(ticketId: string) {
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
        gridTemplateColumns: "48px 280px 1fr 320px",
        gridTemplateRows: "1fr 180px",
      }}
    >
      {/* Icon bar — col 1, rows 1-2 */}
      <div
        className="border-r border-zinc-700"
        style={{ gridColumn: "1", gridRow: "1 / 3" }}
      >
        <IconBar activePanel={panel} onChangePanel={setPanel} />
      </div>

      {/* Sidebar — col 2, rows 1-2 */}
      <div
        className="border-r border-zinc-700 overflow-hidden"
        style={{ gridColumn: "2", gridRow: "1 / 3" }}
      >
        <ErrorBoundary>
          <Sidebar
            panel={panel}
            activeProject={project}
            activeTicket={ticket}
            byStatus={tickets.byStatus}
            ticketsLoading={tickets.loading}
            ticketsError={tickets.error}
            runs={runs.runs}
            runsLoading={runs.loading}
            runsError={runs.error}
            usage={usageData.usage}
            usageLoading={usageData.loading}
            usageError={usageData.error}
            onRefreshUsage={usageData.refresh}
            running={running}
            runningRound={stream.currentRound}
            showKanban={showKanban}
            onSelectProject={handleSelectProject}
            onProjectCreated={handleProjectCreated}
            onSelectTicket={setTicket}
            onRunPipeline={handleRunPipeline}
            onToggleKanban={() => setShowKanban((v) => !v)}
            onTicketCreated={handleTicketCreated}
            onBatchCreated={handleBatchCreated}
            onSelectTicketById={handleSelectTicketById}
            onAgentCreated={handleAgentCreated}
          />
        </ErrorBoundary>
      </div>

      {/* Center — col 3, row 1: Monaco or Kanban */}
      <div
        className="overflow-hidden"
        style={{ gridColumn: "3", gridRow: "1" }}
      >
        <ErrorBoundary>
          {showKanban ? (
            <KanbanView
              byStatus={tickets.byStatus}
              activeTicket={ticket}
              running={running}
              onSelectTicket={setTicket}
              onRunPipeline={handleRunPipeline}
            />
          ) : (
            <Editor ticket={ticket} />
          )}
        </ErrorBoundary>
      </div>

      {/* Agent Panel — col 4, rows 1-2 */}
      <div
        className="overflow-hidden"
        style={{ gridColumn: "4", gridRow: "1 / 3" }}
      >
        <ErrorBoundary>
          <AgentPanel project={project} stream={stream} />
        </ErrorBoundary>
      </div>

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
