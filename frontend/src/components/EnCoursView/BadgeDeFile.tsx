import type { StreamState } from "../../hooks/streamState";

/** Ce que la salle sait du run de pipeline ouvert sur son projet. */
export interface RunDeSalle {
  ticketId: string | null;
  queue: StreamState["queue"];
}

/** « File 3/6 · ticket-059 » pour une file, l'id du ticket seul sinon. */
function libelleDeFile({ ticketId, queue }: RunDeSalle): string {
  const ticket = ticketId ?? "";
  if (queue === null) return ticket;
  const file = `File ${queue.index}/${queue.total}`;
  return ticket === "" ? file : `${file} · ${ticket}`;
}

/**
 * Le badge bleu de la plaque : une file travaille sur ce projet, et sur quel ticket
 * (ticket-712). Ses agents ne se dessinent pas ici : ils sont au Bureau (ticket-729) ;
 * la salle ne montre que les agents du produit.
 */
export default function BadgeDeFile({ run }: { run: RunDeSalle }) {
  return (
    <span
      data-badge-de-file
      className="rounded-sm bg-blue-950 px-2 py-0.5 text-xs font-medium text-blue-300 ring-1 ring-blue-800"
    >
      {libelleDeFile(run)}
    </span>
  );
}
