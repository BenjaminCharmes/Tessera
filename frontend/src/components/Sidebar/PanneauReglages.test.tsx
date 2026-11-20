import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PanneauReglages from "./PanneauReglages";
import type { Reglage } from "../../lib/apiReglages";

const api = vi.hoisted(() => ({
  list: vi.fn(),
  ecrire: vi.fn(),
  retirer: vi.fn(),
}));

vi.mock("../../lib/apiReglages", async () => {
  const reel = await vi.importActual<typeof import("../../lib/apiReglages")>(
    "../../lib/apiReglages",
  );
  return { ...reel, reglages: api };
});

function reglage(surcharge: Partial<Reglage> & { nom: string }): Reglage {
  return {
    libelle: surcharge.nom,
    type: "float",
    valeur: 5,
    defaut: 5,
    minimum: 0.5,
    maximum: 50,
    modifie: false,
    effet: "prochain_run",
    runs_ouverts: 0,
    ...surcharge,
  };
}

function cinq(): Reglage[] {
  return [
    reglage({ nom: "run_max_budget_usd", libelle: "Plafond d'un run" }),
    reglage({ nom: "llm_max_budget_usd", libelle: "Plafond d'un appel", valeur: 1, defaut: 1, minimum: 0.25, maximum: 10 }),
    reglage({ nom: "dialogue_timeout_s", libelle: "Délai de reprise", valeur: 300, defaut: 300, minimum: 30, maximum: 3600 }),
    reglage({ nom: "max_parallel_test_runs", libelle: "Suites simultanées", type: "int", valeur: 2, defaut: 2, minimum: 1, maximum: 8, effet: "machine" }),
    reglage({ nom: "keep_awake_during_runs", libelle: "Machine éveillée", type: "bool", valeur: true, defaut: true, minimum: null, maximum: null, effet: "machine" }),
  ];
}

describe("PanneauReglages", () => {
  beforeEach(() => {
    api.list.mockReset().mockResolvedValue(cinq());
    api.ecrire.mockReset().mockResolvedValue(cinq()[0]);
    api.retirer.mockReset().mockResolvedValue(cinq()[0]);
  });

  it("shows_five_rows_with_their_default", async () => {
    render(<PanneauReglages />);
    expect(await screen.findByLabelText("Plafond d'un run")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
    expect(screen.getAllByText(/Défaut de \.env/)).toHaveLength(5);
    expect(screen.getByText(/Défaut de \.env : 300/)).toBeInTheDocument();
  });

  it("applies_a_value_with_a_put", async () => {
    render(<PanneauReglages />);
    const champ = await screen.findByLabelText("Plafond d'un run");
    await userEvent.clear(champ);
    await userEvent.type(champ, "12");
    await userEvent.click(screen.getAllByRole("button", { name: "Appliquer" })[0]);
    await waitFor(() => expect(api.ecrire).toHaveBeenCalledWith("run_max_budget_usd", 12));
  });

  it("resets_a_setting_with_a_delete", async () => {
    api.list.mockResolvedValue(
      cinq().map((r) => (r.nom === "dialogue_timeout_s" ? { ...r, valeur: 600, modifie: true } : r)),
    );
    render(<PanneauReglages />);
    await userEvent.click(await screen.findByRole("button", { name: "Revenir au défaut" }));
    await waitFor(() => expect(api.retirer).toHaveBeenCalledWith("dialogue_timeout_s"));
  });

  it("shows_the_effect_in_plain_words", async () => {
    render(<PanneauReglages />);
    await screen.findByLabelText("Plafond d'un run");
    expect(screen.getAllByText(/au prochain run/).length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText(/dès la prochaine suite de tests/)).toBeInTheDocument();
  });

  it("shows_how_many_runs_keep_the_old_value", async () => {
    api.list.mockResolvedValue(
      cinq().map((r) => (r.nom === "run_max_budget_usd" ? { ...r, runs_ouverts: 2 } : r)),
    );
    render(<PanneauReglages />);
    expect(await screen.findByText("2 runs gardent l'ancienne valeur")).toBeInTheDocument();
  });

  it("shows_the_error_message_for_a_422_and_a_403", async () => {
    render(<PanneauReglages />);
    const champ = await screen.findByLabelText("Plafond d'un run");
    const appliquer = screen.getAllByRole("button", { name: "Appliquer" })[0];
    api.ecrire.mockRejectedValueOnce(new Error('API 422: {"detail":"doit être entre 0.5 et 50"}'));
    await userEvent.clear(champ);
    await userEvent.type(champ, "7");
    await userEvent.click(appliquer);
    expect(await screen.findByText(/Valeur refusée : doit être entre 0.5 et 50/)).toBeInTheDocument();
    api.ecrire.mockRejectedValueOnce(new Error('API 403: {"detail":"Forbidden"}'));
    await userEvent.click(appliquer);
    expect(await screen.findByText(/origine déclarée/)).toBeInTheDocument();
  });

  it("does_not_offer_zero_for_a_budget", async () => {
    render(<PanneauReglages />);
    const champ = await screen.findByLabelText("Plafond d'un run");
    await userEvent.clear(champ);
    await userEvent.type(champ, "0");
    expect(screen.getAllByRole("button", { name: "Appliquer" })[0]).toBeDisabled();
    expect(champ).toHaveAttribute("min", "0.5");
    expect(api.ecrire).not.toHaveBeenCalled();
  });
});
