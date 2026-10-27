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

function ev(type: OrchestratorEvent["type"], data: Record<string, unknown> = {}, agent: OrchestratorEvent["agent"] = null) {
  return { type, agent, ticket_id: "ticket-001", data, timestamp: T } satisfies OrchestratorEvent;
}

/** Le codeur travaille, puis pose une question que personne n'a encore reprise. */
function enQuestion(): StreamState {
  return [ev("agent_started", {}, "codeur"), ev("agent_question", { question: "Quelle option ?" })].reduce(
    applyEvent,
    INITIAL,
  );
}

/** Le validateur en cours, dont le provider principal vient de tomber. */
function enRepli(): StreamState {
  return [
    ev("validation_started"),
    ev("provider_fallback", { role: "validateur", tente: "ollama", utilise: "anthropic", modele: "haiku" }),
  ].reduce(applyEvent, INITIAL);
}

function salle(nom: string): HTMLElement {
  return screen.getByRole("complementary", { name: nom });
}

describe("SallesCommunes", () => {
  it("renders the four rooms: director, meeting, break, HR", () => {
    render(<SallesCommunes projets={[]} maintenant={T0} />);

    const noms = screen.getAllByRole("complementary").map((s) => s.getAttribute("aria-label"));
    expect(noms).toEqual(["Bureau du directeur", "Salle de réunion", "Salle de pause", "RH"]);
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
      <SallesCommunes projets={[{ nom: "alpha", etat: INITIAL }]} maintenant={T0} />,
    );

    const directeur = salle("Bureau du directeur");
    expect(directeur.querySelectorAll('[data-sprite="personnage"]')).toHaveLength(1);
    expect(directeur.querySelector("[data-agent]")).toBeNull();
    expect(within(directeur).queryByTestId("bulle")).toBeNull();
    expect(directeur).toHaveAttribute("data-contour", "neutre");
    expect(container.querySelector('[data-sprite="bureau-en-bois"]')).not.toBeNull();
  });

  it("brings the agent of a pending question in front of the director, with a '?' bubble", () => {
    render(<SallesCommunes projets={[{ nom: "alpha", etat: enQuestion() }]} maintenant={T0} />);

    const directeur = salle("Bureau du directeur");
    const agent = directeur.querySelector('[data-agent="codeur"]');
    expect(agent).not.toBeNull();
    expect(within(directeur).getByTestId("bulle")).toHaveTextContent("?");
    expect(within(directeur).getByText("alpha")).toBeInTheDocument();
    expect(directeur).toHaveAttribute("data-contour", "amber");
  });

  it("brings the agent of a fallback to HR with 'tenté → utilisé', then lets it leave after 20 s", () => {
    const projets = [{ nom: "alpha", etat: enRepli() }];
    const { rerender } = render(<SallesCommunes projets={projets} maintenant={T0 + 1_000} />);

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

  it("puts a conflict in the meeting room with its number of files", () => {
    const etat = applyEvent(
      INITIAL,
      ev("conflict_resolution", { phase: "started", files: ["a.py", "b.py", "c.py"], outcome: null }),
    );
    render(<SallesCommunes projets={[{ nom: "alpha", etat }]} maintenant={T0} />);

    expect(within(salle("Salle de réunion")).getByText(/3 fichiers/)).toBeInTheDocument();
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
    const { rerender } = render(<Piece projet="alpha" etat={enCours} maintenant={T0} />);
    // Pendant un run, les cinq postes ont leur agent assis.
    expect(personnagesAssis()).toBe(5);

    rerender(<Piece projet="alpha" etat={enQuestion()} maintenant={T0} />);

    expect(personnagesAssis()).toBe(4);
    const poste = screen.getByRole("button", { name: /^Codeur/ }).parentElement;
    expect(poste).toHaveAttribute("data-absent", "true");
    expect(poste?.querySelector('[data-sprite="personnage"]')).toBeNull();
    expect(screen.queryByTestId("bulle")).toBeNull();
  });

  it("seats the agent back at its post once the fallback is 20 s old", () => {
    const { rerender } = render(<Piece projet="alpha" etat={enRepli()} maintenant={T0 + 1_000} />);
    const pendantLeRepli = personnagesAssis();

    rerender(<Piece projet="alpha" etat={enRepli()} maintenant={T0 + 20_000} />);

    expect(personnagesAssis()).toBe(pendantLeRepli + 1);
  });
});
