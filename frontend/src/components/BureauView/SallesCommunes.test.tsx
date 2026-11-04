import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import { api } from "../../lib/api";
import type { OrchestratorEvent } from "../../types/api";
import Piece from "./Piece";
import SallesCommunes from "./SallesCommunes";

const T = "2026-10-27T10:00:00.000Z";
const T0 = Date.parse(T);

function ev(
  type: OrchestratorEvent["type"],
  data: Record<string, unknown> = {},
  agent: OrchestratorEvent["agent"] = null,
) {
  return {
    type,
    agent,
    ticket_id: "ticket-001",
    data,
    timestamp: T,
  } satisfies OrchestratorEvent;
}

/** Le codeur travaille, puis pose une question que personne n'a encore reprise. */
function enQuestion(): StreamState {
  return [
    ev("agent_started", {}, "codeur"),
    ev("agent_question", { question: "Quelle option ?" }),
  ].reduce(applyEvent, INITIAL);
}

/** Le validateur en cours, dont le provider principal vient de tomber. */
function enRepli(): StreamState {
  return [
    ev("validation_started"),
    ev("provider_fallback", {
      role: "validateur",
      tente: "ollama",
      utilise: "anthropic",
      modele: "haiku",
    }),
  ].reduce(applyEvent, INITIAL);
}

function salle(nom: string): HTMLElement {
  return screen.getByRole("complementary", { name: nom });
}

describe("SallesCommunes", () => {
  it("renders the four rooms: director, meeting, break, HR", () => {
    render(<SallesCommunes projets={[]} maintenant={T0} />);

    const noms = screen
      .getAllByRole("complementary")
      .map((s) => s.getAttribute("aria-label"));
    expect(noms).toEqual([
      "Bureau du directeur",
      "Salle de réunion",
      "Salle de pause",
      "RH",
    ]);
  });

  it("carries each room's explanation in a title and writes none under it", () => {
    render(<SallesCommunes projets={[]} maintenant={T0} />);

    for (const s of screen.getAllByRole("complementary")) {
      const titre = within(s).getByRole("heading");
      const phrase = titre.getAttribute("title") ?? "";
      expect(phrase.length).toBeGreaterThan(10);
      expect(within(s).queryByText(phrase)).toBeNull();
      expect(titre.querySelector('[data-marque="info"]')).not.toBeNull();
    }
  });

  it("shows only the director when no question waits", () => {
    const { container } = render(
      <SallesCommunes
        projets={[{ nom: "alpha", etat: INITIAL }]}
        maintenant={T0}
      />,
    );

    const directeur = salle("Bureau du directeur");
    expect(
      directeur.querySelectorAll("[data-pose]"),
    ).toHaveLength(1);
    expect(directeur.querySelector("[data-agent]")).toBeNull();
    expect(within(directeur).queryByTestId("bulle")).toBeNull();
    expect(directeur).toHaveAttribute("data-contour", "neutre");
    expect(
      container.querySelector('[data-sprite="bureau-en-bois"]'),
    ).not.toBeNull();
  });

  it("brings the agent of a pending question in front of the director, with a '?' bubble", () => {
    render(
      <SallesCommunes
        projets={[{ nom: "alpha", etat: enQuestion() }]}
        maintenant={T0}
      />,
    );

    const directeur = salle("Bureau du directeur");
    const agent = directeur.querySelector('[data-agent="codeur"]');
    expect(agent).not.toBeNull();
    expect(within(directeur).getByTestId("bulle")).toHaveTextContent("?");
    expect(within(directeur).getByText("alpha")).toBeInTheDocument();
    expect(directeur).toHaveAttribute("data-contour", "amber");
  });

  it("brings the agent of a fallback to HR with 'tenté → utilisé', then lets it leave after 20 s", () => {
    const projets = [{ nom: "alpha", etat: enRepli() }];
    const { rerender } = render(
      <SallesCommunes projets={projets} maintenant={T0 + 1_000} />,
    );

    const rh = salle("RH");
    expect(rh.querySelector('[data-agent="validateur"]')).not.toBeNull();
    const etiquette = within(rh).getByLabelText("ollama vers anthropic");
    expect(etiquette).toHaveTextContent("ollamaanthropic");
    expect(rh).toHaveAttribute("data-contour", "amber");

    rerender(<SallesCommunes projets={projets} maintenant={T0 + 20_000} />);

    expect(salle("RH").querySelector("[data-agent]")).toBeNull();
    expect(screen.queryByLabelText("ollama vers anthropic")).toBeNull();
    expect(salle("RH")).toHaveAttribute("data-contour", "neutre");
  });

  it("writes who is in a room in its header, never on its floor where the decor covered it", () => {
    // Le 28/10, « alpha · Codeur » se lisait derrière la bibliothèque du directeur (ticket-637).
    render(
      <SallesCommunes
        projets={[{ nom: "alpha", etat: enQuestion() }]}
        maintenant={T0}
      />,
    );

    const directeur = salle("Bureau du directeur");
    const texte = within(directeur).getByText("alpha");
    expect(texte.closest("[data-sol]")).toBeNull();
    expect(directeur.querySelector("[data-sol] [data-agent]")).not.toBeNull();
    expect(
      within(directeur).queryByText("Aucune question en attente"),
    ).toBeNull();
  });

  it("puts a conflict in the meeting room with its number of files", () => {
    const etat = applyEvent(
      INITIAL,
      ev("conflict_resolution", {
        phase: "started",
        files: ["a.py", "b.py", "c.py"],
        outcome: null,
      }),
    );
    render(
      <SallesCommunes projets={[{ nom: "alpha", etat }]} maintenant={T0} />,
    );

    expect(
      within(salle("Salle de réunion")).getByText(/3 fichiers/),
    ).toBeInTheDocument();
  });

  it("draws the resolver while a conflict has no outcome, and not once it has one", () => {
    const enCours = applyEvent(
      INITIAL,
      ev("conflict_resolution", { phase: "started", files: ["a.py"], outcome: null }),
    );
    const { container, rerender } = render(
      <SallesCommunes projets={[{ nom: "alpha", etat: enCours }]} maintenant={T0} />,
    );
    expect(salle("Salle de réunion").querySelector('[data-agent="resolveur"]')).not.toBeNull();

    const fini = applyEvent(
      enCours,
      ev("conflict_resolution", { phase: "done", files: ["a.py"], outcome: "resolved" }),
    );
    rerender(<SallesCommunes projets={[{ nom: "alpha", etat: fini }]} maintenant={T0} />);

    expect(container.querySelector('[data-agent="resolveur"]')).toBeNull();
  });
});

describe("Piece with an agent away", () => {
  beforeEach(() => {
    vi.spyOn(api.services, "list").mockResolvedValue([]);
    vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function personnagesAssis(): number {
    const section = screen.getByRole("region", { name: "alpha" });
    return section.querySelectorAll('[data-pose="assis"]').length;
  }

  it("draws no character at the post of an agent waiting in front of the director", () => {
    const enCours = applyEvent(INITIAL, ev("agent_started", {}, "codeur"));
    const { rerender } = render(
      <Piece projet="alpha" etat={enCours} maintenant={T0} />,
    );
    // Pendant un run, les cinq postes ont leur agent assis.
    expect(personnagesAssis()).toBe(5);

    rerender(<Piece projet="alpha" etat={enQuestion()} maintenant={T0} />);

    expect(personnagesAssis()).toBe(4);
    const poste = screen.getByRole("button", { name: /, codeur, / }).parentElement;
    expect(poste).toHaveAttribute("data-absent", "true");
    expect(poste?.querySelector("[data-pose]")).toBeNull();
    expect(screen.queryByTestId("bulle")).toBeNull();
  });

  it("seats the agent back at its post once the fallback is 20 s old", () => {
    const { rerender } = render(
      <Piece projet="alpha" etat={enRepli()} maintenant={T0 + 1_000} />,
    );
    const pendantLeRepli = personnagesAssis();

    rerender(
      <Piece projet="alpha" etat={enRepli()} maintenant={T0 + 20_000} />,
    );

    expect(personnagesAssis()).toBe(pendantLeRepli + 1);
  });
});

describe("SallesCommunes — des occupants dans la salle de pause et la salle de réunion (ticket-784)", () => {
  function pause(): HTMLElement {
    return salle("Salle de pause");
  }

  it("seats the validator with the PR while its CI runs, even once the queue has moved on", () => {
    const enCi = [
      ev("livraison_done", { pr_number: 853, arret: null, conflits: [] }),
      // La file passe au ticket suivant pendant la CI : seule `events` garde la livraison.
      ev("queue_progress", { index: 2, total: 3, restants: [], faits: ["ticket-001"] }),
      ev("agent_started", {}, "codeur"),
    ].reduce(applyEvent, INITIAL);
    const { rerender } = render(<SallesCommunes projets={[{ nom: "alpha", etat: enCi }]} maintenant={T0} />);

    expect(within(pause()).getByText(/CI en cours de la PR #853/)).toBeInTheDocument();
    const validateur = pause().querySelector('[data-agent="validateur"]');
    expect(validateur).not.toBeNull();
    expect(validateur?.getAttribute("data-objet")).toBe("pr");

    const merge = applyEvent(enCi, ev("ci_merge_done", { pr_number: 853, merged: true }));
    rerender(<SallesCommunes projets={[{ nom: "alpha", etat: merge }]} maintenant={T0} />);
    expect(pause().querySelector("[data-agent]")).toBeNull();
  });

  it("gives the coder and the reviewer a coffee break while the quota is exhausted", () => {
    const etat = applyEvent(INITIAL, ev("error", { reason: "quota_exhausted", resume: "14:00" }));
    render(<SallesCommunes projets={[{ nom: "alpha", etat }]} maintenant={T0} />);

    expect(pause().querySelector('[data-agent="codeur"]')).not.toBeNull();
    expect(pause().querySelector('[data-agent="reviewer"]')).not.toBeNull();
  });

  it("has the coder wait by the coffee machine for a dependency to merge", () => {
    const etat = applyEvent(INITIAL, ev("external_wait", { waiting: true, reason: "dependency", pr_number: 900 }));
    render(<SallesCommunes projets={[{ nom: "alpha", etat }]} maintenant={T0} />);

    expect(within(pause()).getByText(/Attend le merge de la PR #900/)).toBeInTheDocument();
    expect(pause().querySelector('[data-agent="codeur"]')).not.toBeNull();
  });

  it("brings the reviewer to the table with the resolver during a conflict", () => {
    const etat = applyEvent(INITIAL, ev("conflict_resolution", { phase: "started", files: ["a.py"], outcome: null }));
    render(<SallesCommunes projets={[{ nom: "alpha", etat }]} maintenant={T0} />);

    const reunion = salle("Salle de réunion");
    expect(reunion.querySelector('[data-agent="resolveur"]')).not.toBeNull();
    expect(reunion.querySelector('[data-agent="reviewer"]')).not.toBeNull();
  });

  it("keeps the resolver, PR in hand, while its resolved conflict waits for a human review", () => {
    const etat = applyEvent(
      INITIAL,
      ev("livraison_done", { pr_number: 77, arret: "conflit résolu par l'agent : relecture humaine", conflits: ["a.py"] }),
    );
    render(<SallesCommunes projets={[{ nom: "alpha", etat }]} maintenant={T0} />);

    const resolveur = salle("Salle de réunion").querySelector('[data-agent="resolveur"]');
    expect(resolveur).not.toBeNull();
    expect(resolveur?.getAttribute("data-objet")).toBe("pr");
  });
});
