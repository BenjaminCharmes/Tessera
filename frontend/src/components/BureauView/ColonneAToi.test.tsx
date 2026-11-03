import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import BureauView from "./index";
import type { ProjetDuBureau } from "./index";
import ColonneAToi from "./ColonneAToi";
import { api } from "../../lib/api";
import { apiQuota } from "../../lib/quota";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import { useNotificationsSysteme } from "../../hooks/useNotificationsSysteme";
import type { AgentRole, EventType, UsageStats } from "../../types/api";
import { DERNIER, T0 } from "./etatsDeTest";

function ev(type: EventType, data: Record<string, unknown> = {}, agent: AgentRole | null = null) {
  return { type, agent, ticket_id: "ticket-001", data, timestamp: DERNIER };
}

function rejouer(...evenements: ReturnType<typeof ev>[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

const HUIT_MINUTES = new Date(T0 + 8 * 60_000).toISOString();

function avecQuestion(): StreamState {
  return rejouer(
    ev("agent_started", {}, "codeur"),
    ev("agent_question", { question: "On casse l'API ?", expire_a: HUIT_MINUTES }),
  );
}

function figee(): StreamState {
  return rejouer(ev("agent_started", {}, "codeur"));
}

function conflitResolu(): StreamState {
  return rejouer(
    ev("livraison_done", { pr_number: 42, conflits: ["a.py"], arret: "conflit résolu", merged: false }),
  );
}

function rendre(projets: ProjetDuBureau[], son = { actif: true, regler: vi.fn() }) {
  const envoyer = vi.fn();
  const vue = render(<BureauView projets={projets} envoyer={envoyer} son={son} />);
  return { envoyer, son, ...vue };
}

describe("ColonneAToi", () => {
  beforeEach(() => {
    vi.spyOn(api.services, "list").mockResolvedValue([]);
    vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
    vi.spyOn(api.usage, "stats").mockResolvedValue({ daily: [] } as unknown as UsageStats);
    vi.spyOn(apiQuota, "fenetres").mockResolvedValue({ windows: {} });
    vi.useFakeTimers();
    vi.setSystemTime(T0 + 5_000);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("shows a pending question with a countdown that follows the clock", () => {
    rendre([{ nom: "projet-a", etat: avecQuestion(), runId: "run-1" }]);

    const colonne = screen.getByRole("complementary", { name: "À toi" });
    expect(within(colonne).getByText("On casse l'API ?")).toBeInTheDocument();
    expect(within(colonne).getByTestId("compte-a-rebours")).toHaveTextContent("7m 55s");

    act(() => {
      vi.advanceTimersByTime(5_000);
    });
    expect(within(colonne).getByTestId("compte-a-rebours")).toHaveTextContent("7m 50s");
  });

  it("sends the typed text as an answer on the run's channel", () => {
    const { envoyer } = rendre([{ nom: "projet-a", etat: avecQuestion(), runId: "run-1" }]);

    fireEvent.change(screen.getByLabelText("Réponse pour projet-a"), { target: { value: "oui" } });
    fireEvent.click(screen.getByRole("button", { name: "Répondre à projet-a" }));

    expect(envoyer).toHaveBeenCalledTimes(1);
    expect(envoyer).toHaveBeenCalledWith("run-1", { type: "answer", text: "oui" });
  });

  it("never draws a 'let the agent choose' button", () => {
    rendre([{ nom: "projet-a", etat: avecQuestion(), runId: "run-1" }]);

    expect(screen.queryByText(/laisser l'agent choisir/i)).not.toBeInTheDocument();
  });

  it("lists a suspected frozen run in the frozen group", () => {
    vi.setSystemTime(T0 + 200_000);
    rendre([{ nom: "projet-b", etat: figee(), runId: "run-2" }]);

    const colonne = screen.getByRole("complementary", { name: "À toi" });
    expect(within(colonne).getByText("Figés")).toBeInTheDocument();
    expect(within(colonne).getByText("projet-b")).toBeInTheDocument();
    expect(within(colonne).getByText("figé ?")).toBeInTheDocument();
  });

  it("lists a resolved-conflict PR with its number", () => {
    rendre([{ nom: "projet-c", etat: conflitResolu(), runId: null }]);

    const colonne = screen.getByRole("complementary", { name: "À toi" });
    expect(within(colonne).getByText("PR à relire")).toBeInTheDocument();
    expect(within(colonne).getByText("PR #42")).toBeInTheDocument();
  });

  it("ignores an ordinary delivery without conflicts", () => {
    const etat = rejouer(ev("livraison_done", { pr_number: 7, conflits: [], arret: null }));
    rendre([{ nom: "projet-c", etat, runId: null }]);

    expect(screen.queryByText("PR à relire")).not.toBeInTheDocument();
    expect(screen.getByText("Rien n'attend ta réponse.")).toBeInTheDocument();
  });

  it("does not offer an answer field when the run is unknown", () => {
    rendre([{ nom: "projet-a", etat: avecQuestion(), runId: null }]);

    expect(screen.getByText("On casse l'API ?")).toBeInTheDocument();
    expect(screen.queryByLabelText("Réponse pour projet-a")).not.toBeInTheDocument();
  });

  it("flips the sound setting through the Bureau button", () => {
    const { son } = rendre([{ nom: "projet-a", etat: INITIAL }], { actif: true, regler: vi.fn() });

    const bouton = screen.getByRole("button", { name: "Son des questions" });
    expect(bouton).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(bouton);

    expect(son.regler).toHaveBeenCalledWith(false);
  });
});

const AUCUN_RUN: never[] = [];
const etatDeVide = () => INITIAL;

/** Le Bureau branché sur la vraie cloche, comme le fera le cockpit. */
function ColonneSurLaCloche() {
  const { cloche } = useNotificationsSysteme({ runs: AUCUN_RUN, etatDe: etatDeVide }, null, vi.fn());
  const son = {
    actif: cloche.reglages.question.son,
    regler: (v: boolean) => cloche.setReglage("question", "son", v),
  };
  const contenu = { questions: [], figes: [], prs: [] };
  return <ColonneAToi contenu={contenu} maintenant={0} onAnswer={vi.fn()} son={son} />;
}

describe("ColonneAToi sur le réglage de la cloche", () => {
  beforeEach(() => window.localStorage.clear());

  it("changes the bell's question sound without creating another setting", () => {
    render(<ColonneSurLaCloche />);
    const cles = () => Object.keys(window.localStorage).sort();
    const lire = () => JSON.parse(window.localStorage.getItem("tessera.ui.notifications.types") ?? "null");
    const avant = cles();
    expect(lire().question.son).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Son des questions" }));

    expect(screen.getByRole("button", { name: "Son des questions" })).toHaveAttribute("aria-pressed", "false");
    expect(lire().question.son).toBe(false);
    expect(lire().question.systeme).toBe(true);
    expect(cles()).toEqual(avant);
  });
});
