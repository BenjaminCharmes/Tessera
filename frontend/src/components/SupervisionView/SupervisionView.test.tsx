import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
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
    observerLeTexte: vi.fn(),
    sortieDuService: () => [],
    signalServices: 0,
    fermerRun: vi.fn(),
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

  it("distingue une session de chat d'un run de pipeline", () => {
    // Un tour de chat ecrit et commite comme un run (ADR-019), mais il n'a ni
    // ticket, ni tours de revue, ni verdict : afficher les etiquettes d'un
    // pipeline donnerait a lire des cases vides comme une information.
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [
              run(),
              run({
                run_id: "run-chat",
                project_id: "portfolio",
                mode: "chat",
                ticket_id: "chat",
              }),
            ],
          },
          { "run-chat": { currentRound: 3 } },
        )}
        projects={PROJETS}
      />,
    );

    expect(screen.getByText("chat")).toBeInTheDocument();
    expect(screen.getByText("conversation")).toBeInTheDocument();
    expect(screen.queryByText("tour 3")).not.toBeInTheDocument();
  });

  it("affiche le panneau Agents pour le run selectionne", () => {
    // Critère ticket-223 : la suppression de la colonne de droite ne doit pas
    // priver Supervision de son panneau Agents. AgentPanel est toujours rendu
    // dans la partie droite de la grille de SupervisionView.
    render(
      <SupervisionView
        supervision={supervision({ runs: [run()] })}
        projects={PROJETS}
      />,
    );
    // AgentPanel affiche systématiquement le titre « Agents » dans son header.
    expect(screen.getByText("Agents")).toBeInTheDocument();
  });

  it("compte le chat parmi ce qui tourne", () => {
    // Le badge doit dire ce que l'IDE fait, pas seulement ses pipelines.
    const sup = supervision({
      runs: [run(), run({ run_id: "run-chat", mode: "chat" })],
    });
    expect(sup.runs).toHaveLength(2);
  });

  it("liste les services separement des runs", () => {
    // Un service n'a ni ticket, ni tours, ni verdict, et ne se termine pas
    // tout seul : le meler aux runs donnerait un chrono qui monte
    // indefiniment a cote de pipelines qui finissent.
    render(
      <SupervisionView
        supervision={supervision({ runs: [run()] })}
        projects={PROJETS}
        services={[
          {
            nom: "backend",
            project_id: "ide-core",
            pid: 1,
            demarre_a: new Date().toISOString(),
            en_cours: true,
            code_de_sortie: null,
          },
        ]}
      />,
    );

    const bande = screen.getByLabelText("Services lancés");
    expect(bande).toBeInTheDocument();
    expect(bande.textContent).toContain("backend");
  });

  it("montre en rouge un service mort de lui-meme", () => {
    render(
      <SupervisionView
        supervision={supervision()}
        projects={PROJETS}
        services={[
          {
            nom: "backend",
            project_id: "ide-core",
            pid: 1,
            demarre_a: new Date().toISOString(),
            en_cours: false,
            code_de_sortie: 1,
          },
        ]}
      />,
    );

    const etiquette = screen.getByTitle(/ide-core/);
    expect(etiquette.className).toMatch(/red/);
    expect(etiquette.textContent).toContain("code 1");
  });

  it("ne dit pas « rien en cours » quand des services tournent", () => {
    // « Aucun run en cours » tout court laisserait croire que l'IDE ne fait
    // rien, alors qu'un serveur qu'il a lance ecoute un port.
    render(
      <SupervisionView
        supervision={supervision()}
        projects={PROJETS}
        services={[
          {
            nom: "backend",
            project_id: "ide-core",
            pid: 1,
            demarre_a: new Date().toISOString(),
            en_cours: true,
            code_de_sortie: null,
          },
        ]}
      />,
    );

    expect(screen.getByText(/des services tournent/)).toBeInTheDocument();
  });
});

describe("SupervisionView — run en attente en priorité (ticket-266)", () => {
  it("place la carte d'un run en attente en tete de liste", () => {
    // Deux runs : le second attend une réponse. Sa carte doit être rendue
    // avant celle du premier.
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [
              run({ run_id: "run-1", project_id: "ide-core", ticket_id: "ticket-001" }),
              run({ run_id: "run-2", project_id: "portfolio", ticket_id: "ticket-009" }),
            ],
          },
          { "run-2": { pendingQuestion: "On casse l'API ?" } },
        )}
        projects={PROJETS}
      />,
    );

    const carteIdeCore = screen.getByLabelText("Run ticket-001 sur ide-core");
    const cartePortfolio = screen.getByLabelText("Run ticket-009 sur portfolio");
    // portfolio (run-2, en attente) doit précéder ide-core (run-1) dans le DOM.
    expect(
      cartePortfolio.compareDocumentPosition(carteIdeCore) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  it("selectionne par defaut le run qui attend une reponse", () => {
    // Sans sélection explicite, le panneau de détail montre le run en attente.
    // Le champ de réponse (label « Votre réponse ») n'apparaît que dans
    // AgentDialogue côté panneau — pas dans la carte — donc sa présence
    // confirme que le bon run est affiché.
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [
              run({ run_id: "run-1", project_id: "ide-core", ticket_id: "ticket-001" }),
              run({ run_id: "run-2", project_id: "portfolio", ticket_id: "ticket-009" }),
            ],
            selection: null,
          },
          { "run-2": { pendingQuestion: "On casse l'API ?", status: "running" } },
        )}
        projects={PROJETS}
      />,
    );

    expect(screen.getByLabelText(/Votre réponse/i)).toBeInTheDocument();
  });

  it("garde la carte selectionnee explicitement meme si un autre run attend", () => {
    // Un clic de l'utilisateur sur run-1 doit rester prioritaire sur la
    // sélection automatique vers run-2 qui attend.
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [
              run({ run_id: "run-1", project_id: "ide-core", ticket_id: "ticket-001" }),
              run({ run_id: "run-2", project_id: "portfolio", ticket_id: "ticket-009" }),
            ],
            selection: "run-1",
          },
          {
            "run-1": { status: "running" },
            "run-2": { pendingQuestion: "On casse l'API ?", status: "running" },
          },
        )}
        projects={PROJETS}
      />,
    );

    // AgentDialogue de run-1 : pas de pendingQuestion → pas de champ « Votre réponse ».
    expect(screen.queryByLabelText(/Votre réponse/i)).not.toBeInTheDocument();
  });

  it("le bouton Repondre selectionne le run et donne le focus au champ", async () => {
    // run-2 est déjà sélectionné (selection: "run-2") : AgentDialogue est rendu,
    // l'input #dialogue-reponse est dans le DOM, le focus est donc synchrone.
    const selectionner = vi.fn();
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [
              run({ run_id: "run-1", project_id: "ide-core", ticket_id: "ticket-001" }),
              run({ run_id: "run-2", project_id: "portfolio", ticket_id: "ticket-009" }),
            ],
            selection: "run-2",
            selectionner,
          },
          { "run-2": { pendingQuestion: "On casse l'API ?", status: "running" } },
        )}
        projects={PROJETS}
      />,
    );

    // Le bouton « Répondre » de la carte (pas celui d'AgentDialogue).
    const carte = screen.getByLabelText("Run ticket-009 sur portfolio");
    const bouton = within(carte).getByRole("button", { name: /Répondre/i });
    await userEvent.click(bouton);

    expect(selectionner).toHaveBeenCalledWith("run-2");
    expect(document.getElementById("dialogue-reponse")).toHaveFocus();
  });
});

describe("SupervisionView — bouton Fermer (ticket-267)", () => {
  it("ne rend pas Fermer avant run_closed meme si le pipeline est done", () => {
    // Entre pipeline_done et run_closed, la livraison tourne encore.
    // Le bouton ne doit pas apparaître : cliquer fermerait un run pas encore libéré.
    render(
      <SupervisionView
        supervision={supervision(
          { runs: [run()] },
          {
            "run-1": {
              status: "done",
              runClosed: false,
              lastResult: {
                ticket_id: "ticket-001",
                final_status: "done",
                rounds: 1,
                approved: true,
              },
            },
          },
        )}
        projects={PROJETS}
      />,
    );
    expect(screen.queryByRole("button", { name: /Fermer/i })).not.toBeInTheDocument();
  });

  it("rend Fermer uniquement apres run_closed", () => {
    render(
      <SupervisionView
        supervision={supervision(
          { runs: [run()] },
          {
            "run-1": {
              status: "done",
              runClosed: true,
              lastResult: {
                ticket_id: "ticket-001",
                final_status: "done",
                rounds: 1,
                approved: true,
              },
            },
          },
        )}
        projects={PROJETS}
      />,
    );
    expect(screen.getByRole("button", { name: /Fermer/i })).toBeInTheDocument();
  });

  it("Fermer porte la classe inline-flex (ticket-267)", () => {
    render(
      <SupervisionView
        supervision={supervision(
          { runs: [run()] },
          {
            "run-1": {
              status: "done",
              runClosed: true,
              lastResult: {
                ticket_id: "ticket-001",
                final_status: "done",
                rounds: 1,
                approved: true,
              },
            },
          },
        )}
        projects={PROJETS}
      />,
    );
    const bouton = screen.getByRole("button", { name: /Fermer/i });
    expect(bouton.className).toContain("inline-flex");
  });

  it("un clic sur Fermer appelle fermerRun avec le bon run_id", async () => {
    const fermerRun = vi.fn();
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [run()],
            fermerRun,
          },
          {
            "run-1": {
              status: "done",
              runClosed: true,
              lastResult: {
                ticket_id: "ticket-001",
                final_status: "done",
                rounds: 1,
                approved: true,
              },
            },
          },
        )}
        projects={PROJETS}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /Fermer/i }));
    expect(fermerRun).toHaveBeenCalledWith("run-1");
  });
});
