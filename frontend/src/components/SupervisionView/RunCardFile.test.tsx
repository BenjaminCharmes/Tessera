import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import RunCard from "./RunCard";
import { INITIAL } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";

function run(over: Partial<RunActif> = {}): RunActif {
  return {
    run_id: "r1",
    project_id: "demineur",
    mode: "queue",
    ticket_id: "ticket-004",
    etape: null,
    agent: null,
    tour: 0,
    tokens_entree: 0,
    tokens_sortie: 0,
    cout_usd: 0,
    verdict: null,
    question: null,
    file_index: 2,
    file_total: 3,
    file_restants: ["ticket-005"],
    demarre_a: new Date().toISOString(),
    ...over,
  };
}

function rendre(r: RunActif) {
  return render(
    <RunCard run={r} etat={INITIAL} selectionne={false} onSelect={vi.fn()} />,
  );
}

describe("RunCard — où en est une file (ticket-172)", () => {
  it("affiche l'avancement de la file", () => {
    // La carte disait « file » sans dire s'il en restait deux derrière.
    rendre(run());

    expect(screen.getByText(/2\s*\/\s*3/)).toBeInTheDocument();
  });

  it("nomme les tickets qui restent", () => {
    rendre(run({ file_restants: ["ticket-005", "ticket-006"] }));

    expect(screen.getByText(/ticket-005/)).toBeInTheDocument();
    expect(screen.getByText(/ticket-006/)).toBeInTheDocument();
  });

  it("un run unique n'affiche aucun avancement", () => {
    rendre(
      run({ mode: "single", file_index: 0, file_total: 0, file_restants: [] }),
    );

    expect(screen.queryByText(/\d+\s*\/\s*\d+/)).toBeNull();
  });
});

describe("RunCard — la file se déplie (ticket-179)", () => {
  it("montre les tickets faits quand on déplie", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    rendre(
      run({
        file_faits: ["ticket-001", "ticket-002"],
        file_restants: ["ticket-005"],
      }),
    );

    await userEvent.click(screen.getByText("la file"));

    expect(screen.getByText(/fait · ticket-001/)).toBeInTheDocument();
    expect(screen.getByText(/ensuite · ticket-005/)).toBeInTheDocument();
  });

  it("est repliée par défaut", () => {
    rendre(run({ file_faits: ["ticket-001"] }));

    expect(screen.getByText("la file").closest("details")?.open).toBe(false);
  });

  it("un run unique n'affiche aucune file", () => {
    rendre(
      run({ mode: "single", file_total: 0, file_restants: [], file_faits: [] }),
    );

    expect(screen.queryByText("la file")).toBeNull();
  });
});

describe("RunCard — titre du ticket (ticket-286)", () => {
  it("affiche le titre sous le numéro du ticket", () => {
    rendre(run({ ticket_titre: "Implémenter la feature X" }));
    expect(screen.getByText("Implémenter la feature X")).toBeInTheDocument();
  });

  it("expose le titre complet dans l'attribut title", () => {
    rendre(run({ ticket_titre: "Mon titre complet" }));
    const elem = screen.getByTitle("Mon titre complet");
    expect(elem).toBeInTheDocument();
  });

  it("n'affiche pas de ligne de titre si le titre est absent", () => {
    rendre(run({ ticket_titre: undefined }));
    // Le ticket_id est affiché mais pas de ligne de titre supplémentaire
    expect(screen.getByText("ticket-004")).toBeInTheDocument();
    expect(screen.queryByTitle(/./)).toBeNull();
  });
});

describe("RunCard — état CI de la PR livrée (ticket-308)", () => {
  it("affiche en attente de CI quand livraison_done est reçu mais pas ci_merge_done", () => {
    // ADR-026 : amber pour l'attente.
    render(
      <RunCard
        run={run()}
        etat={{ ...INITIAL, runClosed: true, livraisonPrNumber: 42, ciMerge: null }}
        selectionne={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("PR #42 — en attente de CI")).toBeInTheDocument();
    expect(screen.getByText("PR #42 — en attente de CI").className).toMatch(/amber/);
  });

  it("affiche 'PR #N mergée' apres ci_merge_done avec merged: true", () => {
    // ADR-026 : green pour le succès.
    render(
      <RunCard
        run={run()}
        etat={{
          ...INITIAL,
          runClosed: true,
          livraisonPrNumber: 42,
          ciMerge: { merged: true, arret: null },
        }}
        selectionne={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("PR #42 mergée")).toBeInTheDocument();
    expect(screen.getByText("PR #42 mergée").className).toMatch(/green/);
  });

  it("affiche l'arret apres ci_merge_done avec merged: false", () => {
    // ADR-026 : red pour l'échec.
    render(
      <RunCard
        run={run()}
        etat={{
          ...INITIAL,
          runClosed: true,
          livraisonPrNumber: 7,
          ciMerge: { merged: false, arret: "CI rouge : la PR #7 reste ouverte." },
        }}
        selectionne={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("CI rouge : la PR #7 reste ouverte.")).toBeInTheDocument();
    expect(screen.getByText("CI rouge : la PR #7 reste ouverte.").className).toMatch(/red/);
  });

  it("n'affiche rien de CI quand livraisonPrNumber est null", () => {
    // Pas de PR ouverte : ni attente, ni résultat.
    render(
      <RunCard
        run={run()}
        etat={{ ...INITIAL, runClosed: true, livraisonPrNumber: null, ciMerge: null }}
        selectionne={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.queryByText(/en attente de CI/)).toBeNull();
    expect(screen.queryByText(/mergée/)).toBeNull();
  });
});

describe("RunCard — coût en direct (ticket-197)", () => {
  it("montre le cout, les appels et les outils depuis l'instantane", () => {
    // Un F5 pendant le run doit retrouver le cumul, pas repartir de zéro.
    rendre(run({ cout_usd: 0.84, appels: 3, outils: 47 }));
    expect(screen.getByText("0,84 $ · 3 appels · 47 outils")).toBeInTheDocument();
  });

  it("passe en amber a 70 % du plafond et en red a 90 %", () => {
    // ADR-026 : amber pour l'alerte, red pour l'échec, jamais de violet.
    const { unmount } = render(
      <RunCard run={run({ cout_usd: 3.6, appels: 2, outils: 0 })} etat={INITIAL} selectionne={false} onSelect={vi.fn()} plafondUsd={5} />,
    );
    expect(screen.getByText(/3,60 \$ .* sur 5,00 \$/)).toHaveClass("text-amber-200");
    unmount();
    render(
      <RunCard run={run({ cout_usd: 4.6, appels: 2, outils: 0 })} etat={INITIAL} selectionne={false} onSelect={vi.fn()} plafondUsd={5} />,
    );
    expect(screen.getByText(/4,60 \$ .* sur 5,00 \$/)).toHaveClass("text-red-200");
  });
});
