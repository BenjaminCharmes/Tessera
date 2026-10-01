import { describe, it, expect, vi, beforeEach } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PanneauUsage from "./PanneauUsage";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

const limits = vi.mocked(api.orchestrator.limits);

beforeEach(() => {
  vi.resetAllMocks();
  limits.mockResolvedValue({ run_max_budget_usd: 0, llm_max_budget_usd: 0 });
});

describe("PanneauUsage", () => {
  it("renders all three period buttons with the active one pressed", async () => {
    render(
      <PanneauUsage
        days={30}
        setDays={() => {}}
        portee="tous"
        setPortee={() => {}}
        projetActifId={null}
      />,
    );

    const group = screen.getByRole("group", { name: "Période" });
    const btn30 = screen.getByRole("button", { name: "30 j" });
    expect(group).toBeInTheDocument();
    expect(btn30).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "7 j" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "90 j" })).toHaveAttribute("aria-pressed", "false");
  });

  it("calls setDays when a period button is clicked", async () => {
    const setDays = vi.fn();
    const user = userEvent.setup();
    render(
      <PanneauUsage
        days={30}
        setDays={setDays}
        portee="tous"
        setPortee={() => {}}
        projetActifId={null}
      />,
    );

    await user.click(screen.getByRole("button", { name: "90 j" }));

    expect(setDays).toHaveBeenCalledWith(90);
  });

  it("disables Ce projet when no project is active", () => {
    render(
      <PanneauUsage
        days={30}
        setDays={() => {}}
        portee="tous"
        setPortee={() => {}}
        projetActifId={null}
      />,
    );

    expect(screen.getByRole("button", { name: "Ce projet" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Tous les projets" })).not.toBeDisabled();
  });

  it("calls setPortee with 'tous' when Tous les projets is clicked", async () => {
    const setPortee = vi.fn();
    const user = userEvent.setup();
    render(
      <PanneauUsage
        days={30}
        setDays={() => {}}
        portee="projet"
        setPortee={setPortee}
        projetActifId="ide-core"
      />,
    );

    await user.click(screen.getByRole("button", { name: "Tous les projets" }));

    expect(setPortee).toHaveBeenCalledWith("tous");
  });

  it("calls setPortee with 'projet' when Ce projet is clicked", async () => {
    const setPortee = vi.fn();
    const user = userEvent.setup();
    render(
      <PanneauUsage
        days={30}
        setDays={() => {}}
        portee="tous"
        setPortee={setPortee}
        projetActifId="ide-core"
      />,
    );

    await user.click(screen.getByRole("button", { name: "Ce projet" }));

    expect(setPortee).toHaveBeenCalledWith("projet");
  });

  it("shows aucun plafond when both limits are zero", async () => {
    limits.mockResolvedValue({ run_max_budget_usd: 0, llm_max_budget_usd: 0 });
    render(
      <PanneauUsage
        days={30}
        setDays={() => {}}
        portee="tous"
        setPortee={() => {}}
        projetActifId={null}
      />,
    );

    expect(await screen.findAllByText("aucun plafond")).toHaveLength(2);
  });

  it("formats limits as dollar amounts when non-zero", async () => {
    limits.mockResolvedValue({ run_max_budget_usd: 1.5, llm_max_budget_usd: 10 });
    render(
      <PanneauUsage
        days={30}
        setDays={() => {}}
        portee="tous"
        setPortee={() => {}}
        projetActifId={null}
      />,
    );

    expect(await screen.findByText("$1.50")).toBeInTheDocument();
    expect(screen.getByText("$10.00")).toBeInTheDocument();
  });
});

// Vérifie que le bouton « Tous les projets » dans la colonne conduit à
// appeler api.usage.stats avec projectId = null (critère d'acceptation ticket-253).
// Ce comportement est le fruit de deux étapes : setPortee("tous") ➜ useCockpit
// passe statsProjectId=null ➜ StatsView reçoit projectId=null.
// On vérifie chaque maillon séparément pour rester en test unitaire.
describe("PanneauUsage — portée vers StatsView", () => {
  it("portee=tous entraîne aria-pressed=true sur Tous les projets", () => {
    render(
      <PanneauUsage
        days={30}
        setDays={() => {}}
        portee="tous"
        setPortee={() => {}}
        projetActifId="ide-core"
      />,
    );

    expect(screen.getByRole("button", { name: "Tous les projets" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Ce projet" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });
});

// Vérifie statiquement l'absence de classes text-violet-* dans le source
// (ADR-026 : le violet s'emploie en fond ou en barre, jamais en texte).
// coherence.test.ts le couvre pour tous les fichiers ; ce test le rend
// visible dans le diff du ticket-253.
describe("PanneauUsage — cohérence visuelle (ADR-026)", () => {
  it("does not use text-violet-* classes", () => {
    const src = readFileSync(join(__dirname, "PanneauUsage.tsx"), "utf-8");
    expect(/text-violet-\d/.test(src)).toBe(false);
  });
});
