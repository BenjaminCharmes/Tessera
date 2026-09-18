import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ModelPicker from "./ModelPicker";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

const agents = vi.mocked(api.git.agents);
const setModel = vi.mocked(api.git.setAgentModel);

const REPONSE = {
  agents: [
    { role: "codeur", model: "claude-sonnet-4-6", max_tokens: 8192, active: true },
  ],
  known_models: ["claude-haiku-4-5", "claude-sonnet-4-6"],
};

describe("ModelPicker", () => {
  beforeEach(() => {
    agents.mockReset();
    setModel.mockReset();
  });

  it("montre le modele utilise par cet agent sur ce projet", async () => {
    agents.mockResolvedValue(REPONSE);

    render(<ModelPicker projectId="p" role="codeur" />);

    expect(await screen.findByRole("combobox")).toHaveValue("claude-sonnet-4-6");
  });

  it("n'offre que des modeles que l'app sait tarifer", async () => {
    // Choisir hors grille fausserait la ventilation des couts, qui est
    // justement ce sur quoi on s'appuie pour descendre en gamme (ticket-080).
    agents.mockResolvedValue(REPONSE);

    render(<ModelPicker projectId="p" role="codeur" />);
    await screen.findByRole("combobox");

    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual([
      "claude-haiku-4-5",
      "claude-sonnet-4-6",
    ]);
  });

  it("enregistre le changement de modele", async () => {
    agents.mockResolvedValue(REPONSE);
    setModel.mockResolvedValue(REPONSE);

    render(<ModelPicker projectId="p" role="codeur" />);
    await userEvent.selectOptions(
      await screen.findByRole("combobox"),
      "claude-haiku-4-5",
    );

    expect(setModel).toHaveBeenCalledWith("p", "codeur", "claude-haiku-4-5");
  });

  it("se tait quand le projet ne declare pas cet agent", async () => {
    agents.mockResolvedValue({ agents: [], known_models: ["claude-haiku-4-5"] });

    const { container } = render(<ModelPicker projectId="p" role="codeur" />);

    await vi.waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
