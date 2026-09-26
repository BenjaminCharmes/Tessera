import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PanneauPipeline from "./PanneauPipeline";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

const get = vi.mocked(api.pipeline.get);
const set = vi.mocked(api.pipeline.set);

const REGLAGES = {
  max_review_rounds: 3,
  testeur_enabled: false,
  test_command: null,
  securite_enabled: true,
  validateur_enabled: false,
  autonomy: "pr",
  merge_without_ci: false,
};

describe("PanneauPipeline", () => {
  beforeEach(() => {
    get.mockReset();
    set.mockReset();
    get.mockResolvedValue(REGLAGES);
    set.mockResolvedValue(REGLAGES);
  });

  it("enregistre un interrupteur avec le seul champ qui change", async () => {
    render(<PanneauPipeline projectId="p" runEnCours={false} />);
    await userEvent.click(await screen.findByLabelText("Validateur"));
    expect(set).toHaveBeenCalledWith("p", { validateur_enabled: true });
  });

  it("demande confirmation avant d'enregistrer merge", async () => {
    // Merger, c'est decider qu'un travail est bon (ADR-029, ADR-045).
    render(<PanneauPipeline projectId="p" runEnCours={false} />);
    await userEvent.selectOptions(await screen.findByLabelText("Autonomie"), "merge");
    expect(set).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Confirmer merge" }));
    expect(set).toHaveBeenCalledWith("p", { autonomy: "merge" });
  });

  it("est en lecture seule pendant un run, et le dit", async () => {
    render(<PanneauPipeline projectId="p" runEnCours={true} />);
    expect(await screen.findByLabelText("Validateur")).toBeDisabled();
    expect(screen.getByLabelText("Autonomie")).toBeDisabled();
    expect(screen.getByText(/run suivant/)).toBeInTheDocument();
  });

  it("n'active pas le testeur sans commande", async () => {
    render(<PanneauPipeline projectId="p" runEnCours={false} />);
    expect(await screen.findByLabelText("Testeur")).toBeDisabled();
  });
});
