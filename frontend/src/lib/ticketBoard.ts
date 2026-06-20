import type { Ticket, TicketStatus } from "../types/api";

export type ByStatus = Record<TicketStatus, Ticket[]>;

const EMPTY_BY_STATUS: ByStatus = {
  todo: [],
  "in-progress": [],
  "in-review": [],
  done: [],
  blocked: [],
  cancelled: [],
};

export function groupByStatus(tickets: Ticket[]): ByStatus {
  const result: ByStatus = {
    todo: [],
    "in-progress": [],
    "in-review": [],
    done: [],
    blocked: [],
    cancelled: [],
  };
  for (const ticket of tickets) {
    result[ticket.status].push(ticket);
  }
  return result;
}

export function moveTicket(
  byStatus: ByStatus,
  ticketId: string,
  newStatus: TicketStatus,
): ByStatus {
  let found: Ticket | null = null;

  const without: ByStatus = {
    todo: [],
    "in-progress": [],
    "in-review": [],
    done: [],
    blocked: [],
    cancelled: [],
  };

  for (const status of Object.keys(byStatus) as TicketStatus[]) {
    for (const ticket of byStatus[status]) {
      if (ticket.id === ticketId) {
        found = ticket;
      } else {
        without[status] = [...without[status], ticket];
      }
    }
  }

  if (!found) return byStatus;

  const updated: Ticket = { ...found, status: newStatus };
  return { ...without, [newStatus]: [...without[newStatus], updated] };
}

export { EMPTY_BY_STATUS };
