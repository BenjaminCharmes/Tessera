import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SupervisionView from "./index";
import { INITIAL } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { UseSupervisionResult } from "../../hooks/useSupervision";
import type { Project, RunActif } from "../../types/api";

function run(over: Partial<RunActif> = {}): RunActif {
  return {
    run_id: "run-1",
    project_id: "ide-core",
    mode: "single",
    ticket_id: "ticket-001",
    etape: null,
    agent: null,
    tour: 0,
    tokens_entree: 0,
    tokens_sortie: 0,
    cout_usd: 0,
    verdict: null,
    demarre_a: new Date().toISOString(),
    ...over,
  };
}

function supervision(
  over: Partial<UseSupervisionResult> = {},
  etats: Record<string, Partial<StreamState>> = {},
): UseSupervisionResult {
  return {
    runs: [],
    selection: null,
    selectionner: vi.fn(),
    etatDe: (runId: string) => ({ ...INITIAL, ...(etats[runId] ?? {}) }),
    connecte: true,
    envoyer: vi.fn(),
    suivre: vi.fn(),
    ...over,
  };
}

const PROJETS: Project[] = [
  { id: "ide-core", name: "ide-core", path: "/p/ide-core" } as Project,
  { id: "portfolio", name: "portfolio", path: "/p/portfolio" } as Project,
];

describe("SupervisionView", () => {
  it("dit qu'il n'y a rien en cours plutot que d'afficher un cadre vide", () => {
    render(
      <SupervisionView supervision={supervision()} projects={PROJETS} />,
    );
    expect(screen.getByText(/Aucun run en cours/)).toBeInTheDocument();
  });

  it("distingue l'attente du canal d'un veritable repos", () => {
    // « Aucun run » alors que la socket n'est pas ouverte serait un mensonge :
    // on ne sait pas encore ce qui tourne.
    render(
      <SupervisionView
        supervision={supervision({ connecte: false })}
        projects={PROJETS}
      />,
    );
    expect(screen.getByText(/En attente du canal/)).toBeInTheDocument();
  });

  it("liste un run par projet quand deux projets tournent", () => {
    // Le parallelisme reel de Tessera (ADR-038) : c'est precisement ce que
    // l'AgentPanel seul ne pouvait pas montrer.
    render(
      <SupervisionView
        supervision={supervision({
          runs: [
            run(),
            run({
              run_id: "run-2",
              project_id: "portfolio",
              ticket_id: "ticket-009",
            }),
          ],
        })}
        projects={PROJETS}
      />,
    );

    // Par le libelle des cartes, et non par le texte brut : le detail a
    // droite reaffiche le nom du projet, et une assertion qui ne dit pas de
    // quelle region elle parle en trouve deux.
    expect(
      screen.getByLabelText("Run ticket-001 sur ide-core"),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Run ticket-009 sur portfolio"),
    ).toBeInTheDocument();
  });

  it("selectionne un run au clic, ce qui declenche son abonnement", () => {
    const selectionner = vi.fn();
    render(
      <SupervisionView
        supervision={supervision({
          runs: [run(), run({ run_id: "run-2", project_id: "portfolio" })],
          selectionner,
        })}
        projects={PROJETS}
      />,
    );

    void userEvent.click(
      screen.getByLabelText("Run ticket-001 sur portfolio"),
    );
    return vi.waitFor(() => expect(selectionner).toHaveBeenCalledWith("run-2"));
  });

  it("signale qu'un agent attend une reponse", () => {
    render(
      <SupervisionView
        supervision={supervision(
          { runs: [run()] },
          { "run-1": { pendingQuestion: "On casse l'API ?" } },
        )}
        projects={PROJETS}
      />,
    );
    expect(screen.getByText("attend une réponse")).toBeInTheDocument();
  });

  it("signale un run bloque", () => {
    render(
      <SupervisionView
        supervision={supervision(
          { runs: [run()] },
          { "run-1": { status: "error", errorMessage: "panne" } },
        )}
        projects={PROJETS}
      />,
    );
    expect(screen.getByText("bloqué")).toBeInTheDocument();
  });
});
