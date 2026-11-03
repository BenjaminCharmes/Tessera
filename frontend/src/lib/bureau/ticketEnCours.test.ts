import { describe, expect, it } from "vitest";
import { INITIAL } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";
import { ticketEnCours } from "./ticketEnCours";

const run = {
  run_id: "r",
  project_id: "p",
  ticket_id: "ticket-001",
  ticket_titre: "Premier",
} as RunActif;

describe("ticketEnCours", () => {
  it("names the run's ticket with its title, even when it is the only one", () => {
    expect(ticketEnCours(INITIAL, run)).toEqual({
      id: "ticket-001",
      titre: "Premier",
    });
  });

  it("follows the queue to its current ticket, and takes the title the run carries for it", () => {
    const etat = { ...INITIAL, ticketId: "ticket-002" };

    expect(ticketEnCours(etat, run)).toEqual({ id: "ticket-002", titre: null });
    expect(
      ticketEnCours(etat, {
        ...run,
        ticket_id: "ticket-002",
        ticket_titre: "Deuxième",
      }),
    ).toEqual({
      id: "ticket-002",
      titre: "Deuxième",
    });
  });

  it("gives nothing without any ticket to name", () => {
    expect(ticketEnCours(INITIAL, undefined)).toBeNull();
  });
});
