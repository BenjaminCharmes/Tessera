import { describe, expect, it } from "vitest";
import { T0, etatEnCodage, etatEnSecurite } from "../../components/BureauView/etatsDeTest";
import type { StreamState } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";
import { lignesDeLAgent } from "./agentChoisi";

const RUN: RunActif = {
  run_id: "run-1",
  project_id: "ide-core",
  mode: "ticket",
  ticket_id: "ticket-001",
  etape: null,
  agent: "codeur",
  tour: 1,
  tokens_entree: 0,
  tokens_sortie: 0,
  cout_usd: 0,
  verdict: null,
  demarre_a: "2026-10-23T09:59:00.000Z",
};

function etatComplet(): StreamState {
  return { ...etatEnCodage(), ticketId: "ticket-001", ticketTitre: "Le panneau", currentRound: 2, maxRounds: 3 };
}

function lignes(etat: StreamState, run?: RunActif): Record<string, string> {
  const rendu = lignesDeLAgent("ide-core", "codeur", etat, T0 + 12_000, run);
  return Object.fromEntries((rendu ?? []).map((l) => [l.libelle, l.valeur]));
}

describe("lignesDeLAgent", () => {
  it("states role, project, ticket, round, last sign and activity", () => {
    expect(lignes(etatComplet())).toEqual({
      Rôle: "Codeur",
      Projet: "ide-core",
      Ticket: "ticket-001 — Le panneau",
      Tour: "2 / 3",
      "Dernier signe de vie": "il y a 12 s",
      "Il fait": "travaille",
    });
  });

  it("drops the title when the state has none", () => {
    expect(lignes({ ...etatComplet(), ticketTitre: null }).Ticket).toBe("ticket-001");
  });

  it("falls back on the run for the ticket", () => {
    const etat = { ...etatComplet(), ticketId: null, ticketTitre: null };

    expect(lignes(etat, { ...RUN, ticket_titre: "Du run" }).Ticket).toBe("ticket-001 — Du run");
    expect(lignes(etat)).not.toHaveProperty("Ticket");
  });

  it("shows the round alone when the maximum is unknown, and none before the first", () => {
    expect(lignes({ ...etatComplet(), maxRounds: null }).Tour).toBe("2");
    expect(lignes({ ...etatComplet(), currentRound: 0 })).not.toHaveProperty("Tour");
  });

  it("drops the last sign when no event time is known", () => {
    expect(lignes({ ...etatComplet(), dernierEvenementA: null })).not.toHaveProperty("Dernier signe de vie");
  });

  it("says a pending question in the activity line", () => {
    const etat = { ...etatComplet(), pendingQuestion: "On casse l'API ?" };

    expect(lignes(etat)["Il fait"]).toBe("question : On casse l'API ?");
  });

  it("has no model line, as nothing in the state carries the model", () => {
    expect(Object.keys(lignes(etatComplet())).join(" ")).not.toMatch(/mod[eè]le/i);
  });

  it("tells what a done agent handed in, and how long ago (ticket-778)", () => {
    const etat = etatEnSecurite();
    const rendu = lignesDeLAgent("ide-core", "codeur", etat, T0 + 120_000);
    const parLibelle = Object.fromEntries((rendu ?? []).map((l) => [l.libelle, l.valeur]));

    expect(parLibelle["Rôle"]).toBe("Codeur");
    expect(parLibelle["A rendu"]).toBe("son code");
    expect(parLibelle["Fini"]).toMatch(/^il y a \d+ (s|min)$/);
    expect(parLibelle).not.toHaveProperty("Il fait");
  });

  it("names the verdict a done reviewer gave", () => {
    const etat = etatEnSecurite();
    const fin = etat.ticketEvents.find((e) => e.type === "agent_done" && e.agent === "codeur");
    const avecRevue: StreamState = {
      ...etat,
      ticketEvents: [
        ...etat.ticketEvents,
        { ...(fin as NonNullable<typeof fin>), agent: "reviewer", data: { verdict: "CHANGES_REQUESTED" } },
      ],
    };
    const rendu = lignesDeLAgent("ide-core", "reviewer", avecRevue, T0);

    expect(rendu?.find((l) => l.libelle === "A rendu")?.valeur).toBe("changements demandés");
  });

  it("tells a waiting agent who works before it (ticket-778)", () => {
    const etat = etatEnSecurite();
    const rendu = lignesDeLAgent("ide-core", "reviewer", etat, T0);

    expect(rendu?.find((l) => l.libelle === "Il attend")?.valeur).toBe("la fin de Sécurité");
  });

  it("still describes the working agent as before", () => {
    expect(lignesDeLAgent("ide-core", "securite", etatEnSecurite(), T0)?.map((l) => l.libelle)).toContain("Il fait");
  });
});
