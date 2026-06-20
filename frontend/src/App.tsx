import { useEffect, useRef, useState } from "react";
import { useActiveProject } from "./hooks/useActiveProject";
import { useTickets } from "./hooks/useTickets";
import { useOrchestratorStream } from "./hooks/useOrchestratorStream";
import Sidebar, { IconBar } from "./components/Sidebar";
import Editor from "./components/Editor";
import KanbanView from "./components/KanbanView";
import AgentPanel from "./components/AgentPanel";
import BottomPanel from "./components/BottomPanel";

type SidebarPanel = "projects" | "tickets";

export default function App() {
  const { project, ticket, setProject, setTicket } = useActiveProject();
  const [panel, setPanel] = useState<SidebarPanel>("projects");
  const [showKanban, setShowKanban] = useState(false);

  const stream = useOrchestratorStream(project?.id ?? null);
  const tickets = useTickets(
    project?.id ?? null,
    stream.status === "running" || stream.status === "connecting",
  );

  // Refresh ticket list when a pipeline completes
  const prevLastResult = useRef(stream.lastResult);
  useEffect(() => {
    if (stream.lastResult && stream.lastResult !== prevLastResult.current) {
      prevLastResult.current = stream.lastResult;
      tickets.refresh();
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

  function handleTicketCreated(t: Parameters<typeof setTicket>[0]) {
    tickets.refresh();
    setTicket(t);
  }

  function handleRunPipeline(ticketId: string) {
    stream.connect(ticketId);
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
        <Sidebar
          panel={panel}
          activeProject={project}
          activeTicket={ticket}
          byStatus={tickets.byStatus}
          ticketsLoading={tickets.loading}
          ticketsError={tickets.error}
          running={running}
          showKanban={showKanban}
          onSelectProject={handleSelectProject}
          onSelectTicket={setTicket}
          onRunPipeline={handleRunPipeline}
          onToggleKanban={() => setShowKanban((v) => !v)}
          onTicketCreated={handleTicketCreated}
        />
      </div>

      {/* Center — col 3, row 1: Monaco or Kanban */}
      <div
        className="overflow-hidden"
        style={{ gridColumn: "3", gridRow: "1" }}
      >
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
      </div>

      {/* Agent Panel — col 4, rows 1-2 */}
      <div
        className="overflow-hidden"
        style={{ gridColumn: "4", gridRow: "1 / 3" }}
      >
        <AgentPanel project={project} stream={stream} />
      </div>

      {/* Bottom Panel — col 3, row 2 */}
      <div
        className="overflow-hidden"
        style={{ gridColumn: "3", gridRow: "2" }}
      >
        <BottomPanel events={stream.events} />
      </div>
    </div>
  );
}
