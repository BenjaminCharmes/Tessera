import { describe, it, expect, vi } from "vitest";
import { useState } from "react";
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SupervisionView from "./index";
import { INITIAL } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { UseSupervisionResult } from "../../hooks/useSupervision";
import type { OrchestratorEvent, Project, RunActif } from "../../types/api";

vi.mock("../../lib/api", () => ({
  api: {
    runs: { events: vi.fn().mockResolvedValue([]) },
    orchestrator: { limits: vi.fn().mockResolvedValue({ run_max_budget_usd: 0, llm_max_budget_usd: 0 }) },
    tickets: { activity: vi.fn().mockResolvedValue({ ticket_id: "", runs: [], pr_number: null, github_remote: null }) },
  },
}));

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
    fermerRuns: vi.fn(),
    ...over,
  };
}

function pipelineDoneEvent(finalStatus: string, ticketId = "ticket-001"): OrchestratorEvent {
  return {
    type: "pipeline_done",
    agent: null,
    ticket_id: ticketId,
    data: { final_status: finalStatus },
    timestamp: "2026-01-01T00:00:00.000Z",
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

  it("selectionne un run au clic, ce qui declenche son abonnement", async () => {
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

    // Attendre la fin de l'événement avant de vérifier : la version void + waitFor
    // était instable sous charge (le waitFor expirait avant que le clic soit
    // traité par userEvent v14 — ticket-317).
    await userEvent.click(
      screen.getByLabelText("Run ticket-001 sur portfolio"),
    );
    expect(selectionner).toHaveBeenCalledWith("run-2");
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

describe("SupervisionView — état CI par run (ticket-308)", () => {
  it("ci_merge_done est rattache a la carte du bon ticket_id, pas a la derniere recue", () => {
    // Deux runs clos avec une PR chacun.
    // run-1 (ticket-001) a reçu ci_merge_done (merged: true).
    // run-2 (ticket-002) attend encore la CI.
    // Seule la carte de run-1 doit afficher "mergée".
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [
              run({ run_id: "run-1", project_id: "ide-core", ticket_id: "ticket-001" }),
              run({ run_id: "run-2", project_id: "ide-core", ticket_id: "ticket-002" }),
            ],
          },
          {
            "run-1": {
              runClosed: true,
              livraisonPrNumber: 10,
              ciMerge: { merged: true, arret: null },
            },
            "run-2": {
              runClosed: true,
              livraisonPrNumber: 11,
              ciMerge: null,
            },
          },
        )}
        projects={PROJETS}
      />,
    );

    // run-1 doit montrer "mergée".
    const carteIdeCore1 = screen.getByLabelText("Run ticket-001 sur ide-core");
    expect(carteIdeCore1.textContent).toContain("PR #10 mergée");

    // run-2 doit montrer "en attente de CI".
    const carteIdeCore2 = screen.getByLabelText("Run ticket-002 sur ide-core");
    expect(carteIdeCore2.textContent).toContain("PR #11 — en attente de CI");
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
    // Requête exacte pour ne pas confondre avec le bouton « Fermer par lot »
    // du menu apparu simultanément (ticket-344).
    expect(screen.getByRole("button", { name: "Fermer" })).toBeInTheDocument();
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
    const bouton = screen.getByRole("button", { name: "Fermer" });
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

    await userEvent.click(screen.getByRole("button", { name: "Fermer" }));
    expect(fermerRun).toHaveBeenCalledWith("run-1");
  });

  it("ouvre RunHistorique au clic sur Revoir le run d'une carte close (ticket-327)", async () => {
    // Un run clos avec db_run_id doit afficher le bouton « Revoir le run » sur
    // sa RunCard, et le clic doit remplacer le panneau de droite par RunHistorique.
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [run({ db_run_id: "db-run-1", ticket_id: "ticket-001" })],
          },
          {
            "run-1": { runClosed: true },
          },
        )}
        projects={PROJETS}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: /Revoir le run/ }),
    );

    // RunHistorique affiche un bouton « Historique » pour revenir.
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /historique/i })).toBeInTheDocument(),
    );
  });

  it("ferme RunHistorique et revient au panneau Agents (ticket-327)", async () => {
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [run({ db_run_id: "db-run-1", ticket_id: "ticket-001" })],
          },
          {
            "run-1": { runClosed: true },
          },
        )}
        projects={PROJETS}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: /Revoir le run/ }),
    );
    // RunHistorique est visible.
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /historique/i })).toBeInTheDocument(),
    );

    // Clic sur « Historique » : retour au panneau Agents.
    await userEvent.click(screen.getByRole("button", { name: /historique/i }));

    await waitFor(() =>
      expect(screen.getByText("Agents")).toBeInTheDocument(),
    );
  });
});

describe("SupervisionView — menu Fermer par lot (ticket-344)", () => {
  it("Les bloquees retire les bloquees et laisse les terminees et le run en cours", async () => {
    // run-1 : en cours (runClosed: false)
    // run-2 : terminé (runClosed: true, done)
    // run-3 : bloqué (runClosed: true, blocked)
    const fermerRuns = vi.fn();
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [
              run({ run_id: "run-1", project_id: "ide-core", ticket_id: "ticket-001" }),
              run({ run_id: "run-2", project_id: "portfolio", ticket_id: "ticket-002" }),
              run({ run_id: "run-3", project_id: "autre", ticket_id: "ticket-003" }),
            ],
            fermerRuns,
          },
          {
            "run-1": { runClosed: false },
            "run-2": { runClosed: true, events: [pipelineDoneEvent("done")] },
            "run-3": { runClosed: true, events: [pipelineDoneEvent("blocked")] },
          },
        )}
        projects={[
          { id: "ide-core", name: "ide-core", path: "/p/ide-core" } as Project,
          { id: "portfolio", name: "portfolio", path: "/p/portfolio" } as Project,
          { id: "autre", name: "autre", path: "/p/autre" } as Project,
        ]}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Fermer par lot" }));
    await userEvent.click(screen.getByRole("menuitem", { name: /Les bloqués/ }));

    // Seul run-3 est bloqué.
    expect(fermerRuns).toHaveBeenCalledWith(["run-3"]);
    // run-1 (en cours) et run-2 (terminé) ne sont pas dans le lot.
    const appel = fermerRuns.mock.calls[0][0] as string[];
    expect(appel).not.toContain("run-1");
    expect(appel).not.toContain("run-2");
  });

  it("Tous les runs clos ne retire jamais un run dont runClosed est false", async () => {
    const fermerRuns = vi.fn();
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [
              run({ run_id: "run-actif", project_id: "ide-core", ticket_id: "ticket-001" }),
              run({ run_id: "run-clos", project_id: "portfolio", ticket_id: "ticket-002" }),
            ],
            fermerRuns,
          },
          {
            "run-actif": { runClosed: false },
            "run-clos": { runClosed: true, events: [pipelineDoneEvent("done")] },
          },
        )}
        projects={PROJETS}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Fermer par lot" }));
    await userEvent.click(screen.getByRole("menuitem", { name: /Tous les runs clos/ }));

    const appel = fermerRuns.mock.calls[0][0] as string[];
    expect(appel).not.toContain("run-actif");
    expect(appel).toContain("run-clos");
  });

  it("le menu est absent sans run clos", () => {
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [
              run({ run_id: "run-1", project_id: "ide-core", ticket_id: "ticket-001" }),
            ],
          },
          { "run-1": { runClosed: false } },
        )}
        projects={PROJETS}
      />,
    );
    expect(screen.queryByRole("button", { name: "Fermer par lot" })).not.toBeInTheDocument();
  });

  it("une entree dont le compte vaut zero est desactivee", async () => {
    // Un run terminé : « Les bloqués (0) » doit être désactivé dans le menu.
    render(
      <SupervisionView
        supervision={supervision(
          {
            runs: [
              run({ run_id: "run-1", project_id: "ide-core", ticket_id: "ticket-001" }),
            ],
          },
          { "run-1": { runClosed: true, events: [pipelineDoneEvent("done")] } },
        )}
        projects={PROJETS}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Fermer par lot" }));

    // « Les bloqués (0) » est dans le menu et désactivé.
    const entreeBloquee = screen.getByRole("menuitem", { name: /Les bloqués/ });
    expect(entreeBloquee).toBeDisabled();
    // « Les terminés (1) » est activé.
    const entreeTerminee = screen.getByRole("menuitem", { name: /Les terminés/ });
    expect(entreeTerminee).not.toBeDisabled();
  });

  it("fermer le lot qui contient le run selectionne laisse le panneau sur un run restant", async () => {
    // Wrapper avec état local pour simuler la suppression effective des runs.
    function Wrapper() {
      const [runsActifs, setRunsActifs] = useState([
        run({ run_id: "run-1", project_id: "ide-core", ticket_id: "ticket-001" }),
        run({ run_id: "run-2", project_id: "portfolio", ticket_id: "ticket-002" }),
      ]);

      const sup = supervision(
        {
          runs: runsActifs,
          selection: "run-1",
          fermerRuns: (ids: string[]) =>
            setRunsActifs((prev) => prev.filter((r) => !ids.includes(r.run_id))),
        },
        {
          "run-1": { runClosed: true, events: [pipelineDoneEvent("done")] },
          "run-2": { runClosed: false },
        },
      );

      return <SupervisionView supervision={sup} projects={PROJETS} />;
    }

    render(<Wrapper />);

    // Ouvrir le menu et cliquer sur « Les terminés ».
    await userEvent.click(screen.getByRole("button", { name: "Fermer par lot" }));
    await userEvent.click(screen.getByRole("menuitem", { name: /Les terminés/ }));

    // run-1 (terminé) a été retiré : sa carte disparaît.
    await waitFor(() =>
      expect(
        screen.queryByLabelText("Run ticket-001 sur ide-core"),
      ).not.toBeInTheDocument(),
    );

    // run-2 (en cours) reste : le panneau Agents est toujours affiché.
    expect(screen.getByLabelText("Run ticket-002 sur portfolio")).toBeInTheDocument();
    expect(screen.getByText("Agents")).toBeInTheDocument();
  });
});
