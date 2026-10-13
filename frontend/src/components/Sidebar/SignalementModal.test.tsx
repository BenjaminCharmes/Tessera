import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SignalementModal from "./SignalementModal";
import { signalerATessera } from "../../lib/api";
import type { Project, Ticket } from "../../types/api";

vi.mock("../../lib/api", () => ({
  signalerATessera: vi.fn(),
}));

const mockSignaler = vi.mocked(signalerATessera);

const projet: Project = {
  id: "lyra",
  name: "Lyra",
  path: "C:\\Users\\moi\\Desktop\\projets\\Lyra",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

const ticketCree = { id: "ticket-409", title: "Le titre" } as Ticket;

async function remplir(titre: string, description: string) {
  if (titre) await userEvent.type(screen.getByLabelText("Titre"), titre);
  if (description) {
    await userEvent.type(screen.getByLabelText("Description"), description);
  }
}

describe("SignalementModal", () => {
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends the project, nature, title and description that were typed", async () => {
    mockSignaler.mockResolvedValue(ticketCree);
    render(<SignalementModal project={projet} onClose={onClose} />);

    await userEvent.click(screen.getByLabelText("Idée"));
    await remplir("Le titre", "La description");
    await userEvent.click(screen.getByRole("button", { name: "Envoyer" }));

    await waitFor(() =>
      expect(mockSignaler).toHaveBeenCalledWith({
        projet: "lyra",
        nature: "idee",
        titre: "Le titre",
        description: "La description",
      }),
    );
  });

  it("keeps submit disabled while the title is empty", async () => {
    render(<SignalementModal project={projet} onClose={onClose} />);
    const envoyer = screen.getByRole("button", { name: "Envoyer" });

    await remplir("", "Une description");
    expect(envoyer).toBeDisabled();

    await remplir("Un titre", "");
    expect(envoyer).toBeEnabled();
  });

  it("keeps submit disabled while the description is empty", async () => {
    render(<SignalementModal project={projet} onClose={onClose} />);

    await remplir("Un titre", "");

    expect(screen.getByRole("button", { name: "Envoyer" })).toBeDisabled();
    expect(mockSignaler).not.toHaveBeenCalled();
  });

  it("shows the created ticket id after a success", async () => {
    mockSignaler.mockResolvedValue(ticketCree);
    render(<SignalementModal project={projet} onClose={onClose} />);

    await remplir("Le titre", "La description");
    await userEvent.click(screen.getByRole("button", { name: "Envoyer" }));

    expect(await screen.findByText("Signalé : ticket-409")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Fermer" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("shows the error and keeps the typed text when the API fails", async () => {
    mockSignaler.mockRejectedValue(new Error("API 404: Projet introuvable"));
    render(<SignalementModal project={projet} onClose={onClose} />);

    await remplir("Le titre", "La description");
    await userEvent.click(screen.getByRole("button", { name: "Envoyer" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Projet introuvable",
    );
    expect(screen.getByLabelText("Titre")).toHaveValue("Le titre");
    expect(screen.getByLabelText("Description")).toHaveValue("La description");
    expect(screen.queryByText(/Signalé :/)).not.toBeInTheDocument();
  });
});
