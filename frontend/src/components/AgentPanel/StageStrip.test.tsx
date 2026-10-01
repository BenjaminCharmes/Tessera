import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StageStrip from "./StageStrip";
import type { OrchestratorEvent } from "../../types/api";

function ev(
  type: OrchestratorEvent["type"],
  data: Record<string, unknown> = {},
  agent: OrchestratorEvent["agent"] = null,
): OrchestratorEvent {
  return {
    type,
    agent,
    ticket_id: "ticket-256",
    data,
    timestamp: new Date().toISOString(),
  } as OrchestratorEvent;
}

const REGLAGES_TOUT = {
  securite_enabled: true,
  validateur_enabled: true,
};

const REGLAGES_SANS_SECURITE = {
  securite_enabled: false,
  validateur_enabled: true,
};

describe("StageStrip — état depuis l'instantané (ticket-256)", () => {
  it("affiche validation en cours quand etape=validation, sans événements", () => {
    render(
      <StageStrip etape="validation" events={[]} reglages={REGLAGES_TOUT} />,
    );
    // La pastille validation doit avoir aria-label indiquant "active"
    expect(screen.getByLabelText(/Validation : active/)).toBeTruthy();
  });

  it("déduit que les étapes antérieures sont faites quand etape=validation", () => {
    render(
      <StageStrip etape="validation" events={[]} reglages={REGLAGES_TOUT} />,
    );
    expect(screen.getByLabelText(/Production : done/)).toBeTruthy();
    expect(screen.getByLabelText(/Sécurité : done/)).toBeTruthy();
    expect(screen.getByLabelText(/Revue : done/)).toBeTruthy();
  });

  it("les étapes postérieures restent à venir", () => {
    render(
      <StageStrip etape="validation" events={[]} reglages={REGLAGES_TOUT} />,
    );
    expect(screen.getByLabelText(/Docs : todo/)).toBeTruthy();
    expect(screen.getByLabelText(/Livraison : todo/)).toBeTruthy();
  });
});

describe("StageStrip — enrichissement par les événements (ticket-256)", () => {
  it("passe validation à done après validation_started puis validation_done approuvé", () => {
    const events = [
      ev("validation_started"),
      ev("validation_done", { approved: true }),
    ];
    render(
      <StageStrip etape={null} events={events} reglages={REGLAGES_TOUT} />,
    );
    expect(screen.getByLabelText(/Validation : done/)).toBeTruthy();
  });

  it("marque validation comme rejected après validation_done refusée", () => {
    const events = [ev("validation_done", { approved: false })];
    render(
      <StageStrip etape={null} events={events} reglages={REGLAGES_TOUT} />,
    );
    expect(screen.getByLabelText(/Validation : rejected/)).toBeTruthy();
  });

  it("marque securite comme rejected après security_audit_done BLOCK", () => {
    const events = [ev("security_audit_done", { verdict: "BLOCK" })];
    render(
      <StageStrip etape={null} events={events} reglages={REGLAGES_TOUT} />,
    );
    expect(screen.getByLabelText(/Sécurité : rejected/)).toBeTruthy();
  });

  it("marque production active depuis agent_started codeur", () => {
    const events = [ev("agent_started", { round: 1 }, "codeur")];
    render(
      <StageStrip etape={null} events={events} reglages={REGLAGES_TOUT} />,
    );
    expect(screen.getByLabelText(/Production : active/)).toBeTruthy();
  });

  it("marque production done depuis agent_done codeur", () => {
    const events = [
      ev("agent_started", { round: 1 }, "codeur"),
      ev("agent_done", {}, "codeur"),
    ];
    render(
      <StageStrip etape={null} events={events} reglages={REGLAGES_TOUT} />,
    );
    expect(screen.getByLabelText(/Production : done/)).toBeTruthy();
  });
});

describe("StageStrip — étapes inactives (ticket-256)", () => {
  it("n'affiche pas de pastille sécurité quand securite_enabled=false", () => {
    render(
      <StageStrip etape={null} events={[]} reglages={REGLAGES_SANS_SECURITE} />,
    );
    expect(screen.queryByLabelText(/Sécurité/)).toBeNull();
  });

  it("affiche bien validation quand validateur_enabled=true", () => {
    render(
      <StageStrip etape={null} events={[]} reglages={REGLAGES_SANS_SECURITE} />,
    );
    expect(screen.getByLabelText(/Validation/)).toBeTruthy();
  });

  it("déduit les étapes actives depuis les événements si reglages absent", () => {
    // Sécurité absente des reglages mais visible depuis un événement reçu.
    const events = [ev("security_audit_started")];
    render(<StageStrip etape={null} events={events} />);
    expect(screen.getByLabelText(/Sécurité/)).toBeTruthy();
  });

  it("n'affiche que production et revue sans reglages ni événements", () => {
    render(<StageStrip etape={null} events={[]} />);
    expect(screen.getByLabelText(/Production/)).toBeTruthy();
    expect(screen.getByLabelText(/Revue/)).toBeTruthy();
    expect(screen.queryByLabelText(/Sécurité/)).toBeNull();
    expect(screen.queryByLabelText(/Validation/)).toBeNull();
  });
});
