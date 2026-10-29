import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { EventType, OrchestratorEvent } from "../../types/api";
import { documentationEnCours, livraisonEnCours } from "./suite";

function rejouer(...types: EventType[]): StreamState {
  const evenements: OrchestratorEvent[] = types.map((type) => ({
    type,
    agent: null,
    ticket_id: "ticket-001",
    data: {},
    timestamp: "2026-10-29T10:00:00.000Z",
  }));
  return evenements.reduce(applyEvent, INITIAL);
}

describe("documentationEnCours", () => {
  it("is false before the documentation starts", () => {
    expect(documentationEnCours(INITIAL)).toBe(false);
    expect(documentationEnCours(rejouer("pipeline_done"))).toBe(false);
  });

  it("is true between documentation_started and its end", () => {
    expect(documentationEnCours(rejouer("pipeline_done", "documentation_started"))).toBe(true);
  });

  it("ends on doc_updated and on documentation_failed", () => {
    expect(documentationEnCours(rejouer("documentation_started", "doc_updated"))).toBe(false);
    expect(documentationEnCours(rejouer("documentation_started", "documentation_failed"))).toBe(false);
  });

  it("ends on the next event that is not neutral when nothing announces its end", () => {
    expect(documentationEnCours(rejouer("documentation_started", "livraison_started"))).toBe(false);
    expect(documentationEnCours(rejouer("documentation_started", "commit_created"))).toBe(false);
  });

  it("stays open through events the documenter may emit itself", () => {
    expect(documentationEnCours(rejouer("documentation_started", "quota_updated", "provider_fallback"))).toBe(true);
  });

  it("is false once the run is closed", () => {
    expect(documentationEnCours(rejouer("documentation_started", "run_closed"))).toBe(false);
  });

  it("starts again with a new documentation_started", () => {
    expect(documentationEnCours(rejouer("documentation_started", "doc_updated", "documentation_started"))).toBe(true);
  });
});

describe("livraisonEnCours", () => {
  it("is false before the delivery starts", () => {
    expect(livraisonEnCours(INITIAL)).toBe(false);
    expect(livraisonEnCours(rejouer("pipeline_done", "documentation_started"))).toBe(false);
  });

  it("is true between livraison_started and livraison_done", () => {
    expect(livraisonEnCours(rejouer("livraison_started"))).toBe(true);
    expect(livraisonEnCours(rejouer("livraison_started", "quota_updated"))).toBe(true);
  });

  it("is false once livraison_done arrives, whatever follows", () => {
    expect(livraisonEnCours(rejouer("livraison_started", "livraison_done"))).toBe(false);
    expect(livraisonEnCours(rejouer("livraison_started", "livraison_done", "ci_merge_done"))).toBe(false);
  });

  it("is false once the run is closed", () => {
    expect(livraisonEnCours(rejouer("livraison_started", "run_closed"))).toBe(false);
  });
});
