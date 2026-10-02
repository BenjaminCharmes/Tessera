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

describe("StageStrip — fallback verdict pour validation_done sans approved (retour reviewer ticket-279)", () => {
  it("marque validation rejected si verdict=CHANGES_REQUESTED sans approved", () => {
    // Ancien backend : seul `verdict` est émis, pas `approved`.
    const events = [ev("validation_done", { verdict: "CHANGES_REQUESTED" })];
    render(<StageStrip etape={null} events={events} reglages={REGLAGES_TOUT} />);
    expect(screen.getByLabelText(/Validation : rejected/)).toBeTruthy();
  });

  it("marque validation done si verdict=APPROVED sans approved", () => {
    const events = [ev("validation_done", { verdict: "APPROVED" })];
    render(<StageStrip etape={null} events={events} reglages={REGLAGES_TOUT} />);
    expect(screen.getByLabelText(/Validation : done/)).toBeTruthy();
  });

  it("marque validation rejected si etape=validation et verdict=CHANGES_REQUESTED sans approved", () => {
    // L'instantané dit que l'étape est active mais l'événement de fin est arrivé.
    const events = [ev("validation_done", { verdict: "CHANGES_REQUESTED" })];
    render(<StageStrip etape="validation" events={events} reglages={REGLAGES_TOUT} />);
    expect(screen.getByLabelText(/Validation : rejected/)).toBeTruthy();
  });
});

describe("StageStrip — etape active ne persiste pas apres son evenement de fin (ticket-279)", () => {
  it("marque livraison done quand livraison_done recu meme si etape=livraison", () => {
    const events = [ev("livraison_started"), ev("livraison_done")];
    render(<StageStrip etape="livraison" events={events} reglages={REGLAGES_TOUT} />);
    expect(screen.getByLabelText(/Livraison : done/)).toBeTruthy();
    expect(screen.queryByLabelText(/Livraison : active/)).toBeNull();
  });

  it("marque documentation done quand doc_updated recu meme si etape=documentation", () => {
    const events = [ev("documentation_started"), ev("doc_updated")];
    render(<StageStrip etape="documentation" events={events} reglages={REGLAGES_TOUT} />);
    expect(screen.getByLabelText(/Docs : done/)).toBeTruthy();
    expect(screen.queryByLabelText(/Docs : active/)).toBeNull();
  });
});

describe("StageStrip — étapes parallèles revue + validation (ticket-290)", () => {
  it("affiche revue et validation toutes deux actives quand etapesEnCours les contient", () => {
    const events = [
      ev("agent_started", { round: 1 }, "reviewer"),
      ev("validation_started"),
    ];
    render(
      <StageStrip
        etape="revue"
        etapesEnCours={["revue", "validation"]}
        events={events}
        reglages={REGLAGES_TOUT}
      />,
    );
    expect(screen.getByLabelText(/Revue : active/)).toBeTruthy();
    expect(screen.getByLabelText(/Validation : active/)).toBeTruthy();
  });

  it("maintient revue active, et non done, quand validation_done arrive en premier", () => {
    const events = [
      ev("agent_started", { round: 1 }, "reviewer"),
      ev("validation_started"),
      ev("validation_done", { approved: true }),
    ];
    render(
      <StageStrip
        etape="revue"
        etapesEnCours={["revue"]}
        events={events}
        reglages={REGLAGES_TOUT}
      />,
    );
    // La revue est encore active — son agent_done n'est pas arrivé.
    expect(screen.getByLabelText(/Revue : active/)).toBeTruthy();
    expect(screen.queryByLabelText(/Revue : done/)).toBeNull();
    // La validation est terminée.
    expect(screen.getByLabelText(/Validation : done/)).toBeTruthy();
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
