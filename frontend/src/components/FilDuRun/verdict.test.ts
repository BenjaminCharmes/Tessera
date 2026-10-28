import { describe, it, expect } from "vitest";
import type { OrchestratorEvent } from "../../types/api";
import { revueDeLEvenement, revueSansLigneDeVerdict, verdictDeData, verdictDuReviewer } from "./verdict";

describe("verdictDuReviewer — le champ verdict (ticket-615)", () => {
  it("returns the verdict field even when the text says the opposite", () => {
    expect(verdictDuReviewer({ content: "APPROVED\nTout est bon.", verdict: "CHANGES_REQUESTED" })).toBe(
      "CHANGES_REQUESTED",
    );
    expect(verdictDuReviewer({ content: "CHANGES_REQUESTED\n- un test manque", verdict: "APPROVED" })).toBe(
      "APPROVED",
    );
  });

  it("reads the keyword when the entry carries no verdict", () => {
    expect(verdictDuReviewer({ content: "APPROVED\nOK" })).toBe("APPROVED");
    expect(verdictDuReviewer({ content: "Aucun verdict ici." })).toBe("CHANGES_REQUESTED");
  });
});

describe("verdictDeData / revueDeLEvenement (ticket-615)", () => {
  const evenement = (data: Record<string, unknown>): OrchestratorEvent => ({
    type: "agent_done",
    agent: "reviewer",
    ticket_id: "ticket-001",
    data,
    timestamp: "2026-10-28T09:00:00.000Z",
  });

  it("keeps only a verdict from the vocabulary", () => {
    expect(verdictDeData({ verdict: "APPROVED" })).toBe("APPROVED");
    expect(verdictDeData({ verdict: "MAYBE" })).toBeUndefined();
    expect(verdictDeData({ verdict: 3 })).toBeUndefined();
    expect(verdictDeData({})).toBeUndefined();
  });

  it("extracts content and verdict from an agent_done event", () => {
    expect(revueDeLEvenement(evenement({ content: "texte", verdict: "CHANGES_REQUESTED" }))).toEqual({
      content: "texte",
      verdict: "CHANGES_REQUESTED",
    });
    expect(revueDeLEvenement(evenement({}))).toEqual({ content: "", verdict: undefined });
  });
});

describe("revueSansLigneDeVerdict (ticket-615)", () => {
  it("drops blank lines and the lines that name a verdict", () => {
    expect(revueSansLigneDeVerdict("APPROVED\n\n  Résumé  \nDétail")).toEqual(["Résumé", "Détail"]);
  });
});

describe("verdictDuReviewer — première ligne de verdict l'emporte (ticket-299)", () => {
  it("rend APPROVED quand la première ligne est APPROVED même si CHANGES_REQUESTED apparaît dans le corps", () => {
    const content = "APPROVED\n\n- Bug `CHANGES_REQUESTED` corrigé";
    expect(verdictDuReviewer(content)).toBe("APPROVED");
  });

  it("rend APPROVED pour un **APPROVED** précédé d'une ligne de prose", () => {
    // La prose ne constitue pas une ligne de verdict : **APPROVED** est la première
    // ligne qui commence par un verdict (une fois la décoration retirée).
    const content = "Voici mon avis.\n**APPROVED**";
    expect(verdictDuReviewer(content)).toBe("APPROVED");
  });

  it("rend CHANGES_REQUESTED pour ## CHANGES_REQUESTED: motif en tête", () => {
    const content = "## CHANGES_REQUESTED: le test manque\n\nDétail.";
    expect(verdictDuReviewer(content)).toBe("CHANGES_REQUESTED");
  });

  it("rend CHANGES_REQUESTED quand la réponse ne contient aucun verdict", () => {
    const content = "Voici quelques observations sur le code.";
    expect(verdictDuReviewer(content)).toBe("CHANGES_REQUESTED");
  });
});

describe("verdictDuReviewer — fallback (ticket-299)", () => {
  it("fallback CHANGES_REQUESTED quand le mot apparaît dans le corps sans être en tête de ligne", () => {
    const content = "Voici mon avis.\nIl faudrait CHANGES_REQUESTED pour ce point.";
    expect(verdictDuReviewer(content)).toBe("CHANGES_REQUESTED");
  });

  it("fallback APPROVED quand seul un mot entier APPROVED apparaît dans le corps", () => {
    const content = "Tout semble correct. Je marque APPROVED pour ce diff.";
    expect(verdictDuReviewer(content)).toBe("APPROVED");
  });

  it("fallback refuse 'should not be approved' (pas un mot entier APPROVED isolé)", () => {
    // « approved » en minuscule ne matche pas \bAPPROVED\b (sensible à la casse).
    const content = "Le code ne devrait pas être approved tel quel.";
    expect(verdictDuReviewer(content)).toBe("CHANGES_REQUESTED");
  });

  it("APPROVED dans la première ligne n'approuve pas si CHANGES_REQUESTED suit sur la même ligne", () => {
    const content = "APPROVED serait prématuré : CHANGES_REQUESTED d'abord.";
    expect(verdictDuReviewer(content)).toBe("CHANGES_REQUESTED");
  });
});
