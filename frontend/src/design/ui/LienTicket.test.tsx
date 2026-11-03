import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LienTicket from "./LienTicket";
import { OuvrirTicketContext } from "../../hooks/useOuvrirTicket";
import type { OuvrirTicket, ResultatOuverture } from "../../hooks/useOuvrirTicket";

function rendre(resultat: ResultatOuverture = "ok", projectId: string | null = "p1") {
  const ouvrir = vi.fn<OuvrirTicket>().mockResolvedValue(resultat);
  render(
    <OuvrirTicketContext.Provider value={ouvrir}>
      <LienTicket projectId={projectId} ticketId="ticket-007" />
    </OuvrirTicketContext.Provider>,
  );
  return ouvrir;
}

describe("LienTicket (ticket-460)", () => {
  it("is a button named after the ticket id", () => {
    rendre();
    expect(screen.getByRole("button", { name: "ticket-007" })).toBeInTheDocument();
  });

  it("opens the ticket of its project on click", async () => {
    const ouvrir = rendre();

    await userEvent.click(screen.getByRole("button", { name: "ticket-007" }));

    expect(ouvrir).toHaveBeenCalledWith("p1", "ticket-007");
  });

  it("is reachable with the keyboard and Enter opens the ticket", async () => {
    const ouvrir = rendre();

    await userEvent.tab();
    expect(screen.getByRole("button", { name: "ticket-007" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");

    expect(ouvrir).toHaveBeenCalledWith("p1", "ticket-007");
  });

  it("shows a message, and no error, when the ticket cannot be found", async () => {
    rendre("introuvable");
    expect(screen.queryByRole("status")).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "ticket-007" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Ticket introuvable");
  });

  it("clears the message once the ticket opens", async () => {
    const ouvrir = vi
      .fn<OuvrirTicket>()
      .mockResolvedValueOnce("introuvable")
      .mockResolvedValueOnce("ok");
    render(
      <OuvrirTicketContext.Provider value={ouvrir}>
        <LienTicket projectId="p1" ticketId="ticket-007" />
      </OuvrirTicketContext.Provider>,
    );
    const lien = screen.getByRole("button", { name: "ticket-007" });

    await userEvent.click(lien);
    expect(await screen.findByRole("status")).toBeInTheDocument();
    await userEvent.click(lien);

    expect(screen.queryByRole("status")).toBeNull();
  });

  it("renders plain text when the project is unknown", () => {
    rendre("ok", null);
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByText("ticket-007")).toBeInTheDocument();
  });

  it("says the ticket is missing when rendered without the cockpit", async () => {
    render(<LienTicket projectId="p1" ticketId="ticket-007" />);

    await userEvent.click(screen.getByRole("button", { name: "ticket-007" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Ticket introuvable");
  });
});
