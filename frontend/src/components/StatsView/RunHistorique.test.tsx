import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RunHistorique from "./RunHistorique";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

const mockEvents = vi.mocked(api.runs.events);

describe("RunHistorique — ticket-281", () => {
  it("calls the events endpoint with the run id", async () => {
    mockEvents.mockResolvedValue([]);

    render(<RunHistorique runId="run-abc" ticketId="ticket-042" onClose={() => {}} />);

    await waitFor(() =>
      expect(mockEvents).toHaveBeenCalledWith("run-abc"),
    );
  });

  it("displays agent cards and verdict from replayed events", async () => {
    mockEvents.mockResolvedValue([
      {
        type: "agent_started",
        agent: "codeur",
        data: { round: 1 },
        timestamp: "2026-01-01T00:00:00Z",
      },
      {
        type: "agent_done",
        agent: "codeur",
        data: { content: "Implémentation complète." },
        timestamp: "2026-01-01T00:01:00Z",
      },
      {
        type: "pipeline_done",
        agent: null,
        data: { approved: true, final_status: "done", rounds: 1, ticket_id: "ticket-042" },
        timestamp: "2026-01-01T00:02:00Z",
      },
      {
        type: "run_closed",
        agent: null,
        data: {},
        timestamp: "2026-01-01T00:03:00Z",
      },
    ]);

    render(<RunHistorique runId="run-abc" ticketId="ticket-042" onClose={() => {}} />);

    await screen.findByText("CODEUR");
    expect(screen.getByText("Pipeline terminé")).toBeInTheDocument();
  });

  it("does not show a stop button or a message field", async () => {
    mockEvents.mockResolvedValue([]);

    render(<RunHistorique runId="run-abc" ticketId="ticket-042" onClose={() => {}} />);

    await waitFor(() => expect(mockEvents).toHaveBeenCalled());

    // Aucun bouton d'arrêt, aucun champ de saisie de message
    expect(screen.queryByRole("button", { name: /arrêt|stop/i })).toBeNull();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("shows an error message instead of an empty view when the endpoint fails", async () => {
    mockEvents.mockRejectedValue(new Error("API 404: Run inconnu"));

    render(<RunHistorique runId="unknown-run" ticketId="ticket-042" onClose={() => {}} />);

    const erreur = await screen.findByTestId("run-historique-erreur");
    expect(erreur).toHaveTextContent("API 404");
  });

  it("calls onClose when the back button is clicked", async () => {
    mockEvents.mockResolvedValue([]);
    const handleClose = vi.fn();

    render(<RunHistorique runId="run-abc" ticketId="ticket-042" onClose={handleClose} />);

    await userEvent.click(screen.getByRole("button", { name: /historique/i }));

    expect(handleClose).toHaveBeenCalledOnce();
  });
});
