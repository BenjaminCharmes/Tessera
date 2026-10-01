import { describe, it, expect } from "vitest";
import {
  panelAfterProjectSwitch,
  porteeEffectiveFor,
  runCachePour,
  eventsAffichiesFor,
} from "./useCockpit";
import { INITIAL } from "./streamState";
import type { RunActif, OrchestratorEvent } from "../types/api";

function makeEvent(type: OrchestratorEvent["type"]): OrchestratorEvent {
  return {
    type,
    agent: null,
    ticket_id: "t-1",
    data: {},
    timestamp: new Date().toISOString(),
    run_id: "r-1",
    project_id: "proj-a",
  } as OrchestratorEvent;
}

function makeRun(runId: string, projectId: string): RunActif {
  return {
    run_id: runId,
    project_id: projectId,
    mode: "single",
    ticket_id: null,
    etape: null,
    agent: null,
    tour: 0,
    tokens_entree: 0,
    tokens_sortie: 0,
    cout_usd: 0,
    verdict: null,
    demarre_a: new Date().toISOString(),
  };
}

// Acceptance criteria from ticket-271: switching project must preserve the
// active panel, except when coming from the projects list which opens tickets.
describe("panelAfterProjectSwitch", () => {
  it("keeps the usage panel when changing project", () => {
    expect(panelAfterProjectSwitch("usage")).toBe("usage");
  });

  it("keeps the chat panel when changing project", () => {
    expect(panelAfterProjectSwitch("chat")).toBe("chat");
  });

  it("switches to tickets when the projects panel is active", () => {
    expect(panelAfterProjectSwitch("projects")).toBe("tickets");
  });

  it("keeps every other panel unchanged", () => {
    expect(panelAfterProjectSwitch("tickets")).toBe("tickets");
    expect(panelAfterProjectSwitch("files")).toBe("files");
    expect(panelAfterProjectSwitch("history")).toBe("history");
    expect(panelAfterProjectSwitch("agents")).toBe("agents");
    expect(panelAfterProjectSwitch("supervision")).toBe("supervision");
  });
});

// Acceptance criteria from ticket-258: effective scope must be "tous" when no
// project is active, regardless of the user's prior selection.
describe("porteeEffectiveFor", () => {
  it("returns 'tous' when no project is active, ignoring prior selection", () => {
    expect(porteeEffectiveFor(null, "projet")).toBe("tous");
    expect(porteeEffectiveFor(null, "tous")).toBe("tous");
  });

  it("returns the user's choice when a project is active", () => {
    expect(porteeEffectiveFor({ id: "ide-core" }, "projet")).toBe("projet");
    expect(porteeEffectiveFor({ id: "ide-core" }, "tous")).toBe("tous");
  });
});

// Critères ticket-283 : le bouton « Revenir au run » est proposé dès que le
// run tourne et que le centre affiche autre chose — pas seulement quand
// `runAuPremierPlan` est faux.
describe("runCachePour (ticket-283)", () => {
  it("propose le retour après ouverture d'un fichier pendant un run", () => {
    expect(runCachePour(true, "editor")).toBe(true);
  });

  it("propose le retour après ouverture d'un diff pendant un run", () => {
    expect(runCachePour(true, "diff")).toBe(true);
  });

  it("propose le retour quand le kanban est affiché pendant un run", () => {
    expect(runCachePour(true, "kanban")).toBe(true);
  });

  it("ne propose pas le retour quand le run est au premier plan", () => {
    expect(runCachePour(true, "run")).toBe(false);
  });

  it("ne propose pas le retour sans run en cours", () => {
    expect(runCachePour(false, "editor")).toBe(false);
  });
});

// Critères ticket-283 : le Pipeline log suit le run sélectionné en Supervision.
describe("eventsAffichiesFor (ticket-283)", () => {
  const runEvents: OrchestratorEvent[] = [makeEvent("agent_started")];
  const streamEvents: OrchestratorEvent[] = [makeEvent("pipeline_done")];
  const run = makeRun("run-42", "projet-a");

  const etatDe = (id: string) =>
    id === "run-42" ? { ...INITIAL, events: runEvents } : INITIAL;

  it("affiche les événements du run sélectionné dans la Supervision", () => {
    const result = eventsAffichiesFor("run-42", [run], etatDe, streamEvents);
    expect(result).toBe(runEvents);
  });

  it("affiche les événements du projet actif quand rien n'est sélectionné", () => {
    const result = eventsAffichiesFor(null, [run], etatDe, streamEvents);
    expect(result).toBe(streamEvents);
  });

  it("retombe sur le projet actif si le run sélectionné est inconnu", () => {
    const result = eventsAffichiesFor("run-inconnu", [run], etatDe, streamEvents);
    expect(result).toBe(streamEvents);
  });
});
