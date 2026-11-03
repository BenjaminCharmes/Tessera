import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";
import {
  DELAI_RH_MS,
  agentsAuDirecteur,
  agentsAuxRh,
  lieuxDuRun,
  postesAbsents,
  posteDuRole,
} from "./sallesCommunes";

const T = "2026-10-27T10:00:00.000Z";
const T0 = Date.parse(T);

function ev(type: OrchestratorEvent["type"], data: Record<string, unknown> = {}, agent: OrchestratorEvent["agent"] = null) {
  return { type, agent, ticket_id: "ticket-001", data, timestamp: T } satisfies OrchestratorEvent;
}

function enQuestion(agent: "codeur" | "reviewer" | "architect"): StreamState {
  return [ev("agent_started", {}, agent), ev("agent_question", { question: "Quelle option ?" })].reduce(
    applyEvent,
    INITIAL,
  );
}

function enRepli(role: string): StreamState {
  return applyEvent(
    INITIAL,
    ev("provider_fallback", { role, tente: "ollama", utilise: "anthropic", modele: "haiku" }),
  );
}

describe("posteDuRole", () => {
  it("maps the architect to the coder's post and ignores roles without a post", () => {
    expect(posteDuRole("architect")).toBe("codeur");
    expect(posteDuRole("validateur")).toBe("validateur");
    expect(posteDuRole("resolveur-conflit")).toBeNull();
    expect(posteDuRole(null)).toBeNull();
  });
});

describe("lieuxDuRun", () => {
  it("puts the current agent in front of the director while its question waits", () => {
    expect(lieuxDuRun(enQuestion("reviewer"), T0).directeur).toBe("reviewer");
    expect(lieuxDuRun(enQuestion("architect"), T0).directeur).toBe("codeur");
  });

  it("puts nobody there without a question", () => {
    const etat = applyEvent(INITIAL, ev("agent_started", {}, "codeur"));

    expect(lieuxDuRun(etat, T0).directeur).toBeNull();
  });

  it("brings the agent back once the question has its answer", () => {
    const repondu = applyEvent(enQuestion("codeur"), ev("answer_ack", { outcome: "transmitted" }));

    expect(lieuxDuRun(repondu, T0).directeur).toBeNull();
  });

  it("holds the agent at HR for 20 seconds, not one millisecond more", () => {
    const etat = enRepli("validateur");

    expect(lieuxDuRun(etat, T0 + DELAI_RH_MS - 1).rh?.poste).toBe("validateur");
    expect(lieuxDuRun(etat, T0 + DELAI_RH_MS).rh).toBeNull();
  });

  it("sends nobody to HR for a role that has no post", () => {
    expect(lieuxDuRun(enRepli("doc-technique"), T0).rh).toBeNull();
  });

  it("keeps an agent in one place only: the director wins over HR", () => {
    const etat = applyEvent(enQuestion("codeur"), ev("provider_fallback", { role: "codeur", tente: "a", utilise: "b" }));

    const lieux = lieuxDuRun(etat, T0);
    expect(lieux.directeur).toBe("codeur");
    expect(lieux.rh).toBeNull();
    expect(postesAbsents(etat, T0)).toEqual(["codeur"]);
  });
});

describe("agentsAuDirecteur and agentsAuxRh", () => {
  const projets = [
    { nom: "alpha", etat: enQuestion("codeur") },
    { nom: "beta", etat: enRepli("validateur") },
    { nom: "gamma", etat: INITIAL },
  ];

  it("lists the agents per project, in the order of the projects", () => {
    expect(agentsAuDirecteur(projets, T0)).toEqual([{ projet: "alpha", poste: "codeur" }]);
    expect(agentsAuxRh(projets, T0)).toEqual([
      { projet: "beta", poste: "validateur", tente: "ollama", utilise: "anthropic", modele: "haiku" },
    ]);
  });
});
