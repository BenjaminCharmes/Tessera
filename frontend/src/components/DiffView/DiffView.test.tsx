import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import DiffView from "./index";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

vi.mock("@monaco-editor/react", () => ({
  default: ({ value }: { value: string }) => <pre data-testid="monaco">{value}</pre>,
}));

const diff = vi.mocked(api.tickets.diff);

describe("DiffView", () => {
  beforeEach(() => {
    diff.mockReset();
  });

  it("montre le diff produit par le run", async () => {
    diff.mockResolvedValue({
      ticket_id: "ticket-001",
      branch: "ticket-001-x",
      diff: "-x = 1\n+x = 2",
      files: ["app.py"],
    });

    render(<DiffView projectId="p" ticketId="ticket-001" />);

    expect(await screen.findByTestId("monaco")).toHaveTextContent("+x = 2");
    expect(screen.getByText("app.py")).toBeInTheDocument();
  });

  it("dit qu'un ticket jamais lance n'a pas de branche", async () => {
    diff.mockResolvedValue({
      ticket_id: "ticket-002", branch: null, diff: "", files: [],
    });

    render(<DiffView projectId="p" ticketId="ticket-002" />);

    expect(await screen.findByText(/jamais été lancé/i)).toBeInTheDocument();
  });

  it("distingue une branche sans rien dedans d'un ticket jamais lance", async () => {
    // C'est exactement le cas vecu le 2026-09-17 : deux runs `done`, deux
    // branches creees, aucun commit. L'ecran doit le dire.
    diff.mockResolvedValue({
      ticket_id: "ticket-003", branch: "ticket-003-x", diff: "", files: [],
    });

    render(<DiffView projectId="p" ticketId="ticket-003" />);

    expect(await screen.findByText(/n'a rien produit/i)).toBeInTheDocument();
    expect(screen.getByText("ticket-003-x")).toBeInTheDocument();
  });
});
