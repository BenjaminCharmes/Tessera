import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import { _viderCacheResource } from "../../hooks/useResource";
import { api } from "../../lib/api";
import { statutsDuRun } from "../../lib/statutDuRun";
import { statutDuRun } from "../../test/contrat/exemples";
import DefsDuBureau from "../../design/bureau/DefsDuBureau";
import type { Anomalie, RunActif } from "../../types/api";
import { DERNIER, T0, etatEnCodage } from "./etatsDeTest";
import Piece from "./Piece";

function anomalie(cle: string): Anomalie {
  return {
    regle: "silence", cle, ticket_id: "ticket-001", message: "Aucun événement depuis 15 min sur ce run.",
    mesure: 900, seuil: 900, unite: "s",
  };
}

function run(anomalies: Anomalie[]): RunActif {
  return {
    run_id: "run-1", project_id: "ide-core", mode: "single", ticket_id: "ticket-001", etape: "codage",
    agent: "codeur", tour: 1, tokens_entree: 0, tokens_sortie: 0, cout_usd: 0, verdict: null,
    demarre_a: DERNIER, anomalies,
  };
}

beforeEach(() => {
  _viderCacheResource();
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
  vi.spyOn(api.tickets, "list").mockResolvedValue({ tickets: [], unreadable: [] });
  vi.spyOn(statutsDuRun, "lire").mockResolvedValue(
    statutDuRun({ project_id: "ide-core", mode: "single", statut: "en cours", ticket_courant: "ticket-001", restants: [], debut: DERNIER }),
  );
});

afterEach(() => {
  vi.restoreAllMocks();
});

function piece(anomalies: Anomalie[], etat = etatEnCodage()) {
  return <Piece projet="ide-core" etat={etat} maintenant={T0 + 5_000} run={run(anomalies)} />;
}

describe("the Bureau marks an agent whose run has an anomaly (ticket-832)", () => {
  it("test_bureau_shows_the_anomaly_marker_when_the_run_has_one_anomaly", () => {
    render(piece([anomalie("a")]));

    expect(screen.getByRole("img", { name: "1 anomalie" })).toBeInTheDocument();
  });

  it("test_bureau_shows_no_anomaly_marker_when_the_run_has_none", () => {
    render(piece([]));

    expect(screen.queryByTestId("marqueur-anomalie")).toBeNull();
  });

  it("test_bureau_shows_one_marker_for_a_run_with_three_anomalies", () => {
    render(piece([anomalie("a"), anomalie("b"), anomalie("c")]));

    expect(screen.getAllByTestId("marqueur-anomalie")).toHaveLength(1);
    expect(screen.getByRole("img", { name: "3 anomalies" })).toBeInTheDocument();
  });

  it("puts the marker on the agent at work, above its desk", () => {
    render(piece([anomalie("a")]));

    const poste = screen.getByRole("button", { name: /codeur, travaille/i });
    expect(poste.parentElement).toContainElement(screen.getByTestId("marqueur-anomalie"));
  });

  it("test_bureau_removes_the_marker_when_the_run_closes", () => {
    const { rerender } = render(piece([anomalie("a")]));
    expect(screen.getByTestId("marqueur-anomalie")).toBeInTheDocument();

    const clos = applyEvent(etatEnCodage(), {
      type: "run_closed", agent: null, ticket_id: "ticket-001", data: { approved: true }, timestamp: DERNIER,
    });
    rerender(piece([anomalie("a")], clos));
    expect(screen.queryByTestId("marqueur-anomalie")).toBeNull();

    // Et quand la liste se vide, sur un run encore ouvert.
    rerender(piece([]));
    expect(screen.queryByTestId("marqueur-anomalie")).toBeNull();
  });

  it("test_anomaly_marker_is_a_use_of_the_shared_defs_and_adds_no_inline_path", () => {
    const { container } = render(
      <>
        <DefsDuBureau />
        {piece([anomalie("a")])}
      </>,
    );

    const marqueur = container.querySelector('[data-sprite="anomalie"]') as SVGElement;
    expect(marqueur.querySelectorAll("path")).toHaveLength(0);
    const usages = Array.from(marqueur.querySelectorAll("use"));
    expect(usages.length).toBeGreaterThan(0);
    for (const u of usages) {
      const id = (u.getAttribute("href") ?? "").slice(1);
      expect(id).toMatch(/^sp-/);
      expect(container.querySelector(`[data-defs="bureau"] symbol[id="${id}"]`)).not.toBeNull();
    }
  });

  it("keeps ten marked rooms under the SVG node ceiling of the Bureau (ADR-070)", () => {
    const { container } = render(
      <>
        <DefsDuBureau />
        {Array.from({ length: 10 }, (_, i) => (
          <Piece key={i} projet={`projet-${i}`} etat={etatEnCodage()} maintenant={T0 + 5_000} run={run([anomalie("a"), anomalie("b")])} />
        ))}
      </>,
    );

    expect(screen.getAllByTestId("marqueur-anomalie")).toHaveLength(10);
    // Le plafond de BureauView.test.tsx : dix pièces sous 2250 nœuds, le marqueur compris.
    expect(container.querySelectorAll("svg *").length).toBeLessThan(2250);
  });

  it("test_the_marker_does_not_draw_an_agent_for_a_run_without_activity", () => {
    // ADR-058 et ADR-064 : une donnée ou rien. Aucun événement, donc aucun agent au travail.
    render(piece([anomalie("a")], INITIAL));

    expect(screen.queryByTestId("marqueur-anomalie")).toBeNull();
    expect(screen.queryByTestId("bulle")).toBeNull();
  });
});
