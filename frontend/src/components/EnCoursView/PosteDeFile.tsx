import Agrandi from "../../design/bureau/Agrandi";
import AgentAuPupitre from "../../design/bureau/AgentAuPupitre";
import { TENUES, physiqueDeProduit } from "../../lib/bureau/physique";
import { nomDuPoste } from "../../lib/bureau/libelleDuPoste";
import type { RoleAffiche } from "../../lib/bureau/postesDuRun";
import type { StreamState } from "../../hooks/streamState";

/** Ce que la salle sait du run de pipeline ouvert sur son projet. */
export interface RunDeSalle {
  ticketId: string | null;
  agent: string | null;
  queue: StreamState["queue"];
}

function estRoleAffiche(role: string): role is RoleAffiche {
  return role in TENUES;
}

/** Le nom d'un rôle tel que le Bureau l'écrit ; un rôle inconnu garde son identifiant. */
function nomDuRole(role: string): string {
  return estRoleAffiche(role) ? nomDuPoste(role) : role;
}

/** « File 3/6 · ticket-059 » pour une file, l'id du ticket seul sinon. */
function libelleDeFile({ ticketId, queue }: RunDeSalle): string {
  const ticket = ticketId ?? "";
  if (queue === null) return ticket;
  const file = `File ${queue.index}/${queue.total}`;
  return ticket === "" ? file : `${file} · ${ticket}`;
}

/** Le badge bleu de la plaque : il dit qu'une file travaille ici, et sur quel ticket. */
export function BadgeDeFile({ run }: { run: RunDeSalle }) {
  return (
    <span
      data-badge-de-file
      className="rounded-sm bg-blue-950 px-2 py-0.5 text-xs font-medium text-blue-300 ring-1 ring-blue-800"
    >
      {libelleDeFile(run)}
    </span>
  );
}

/**
 * Le poste de travail du pipeline, au sol de la salle — ticket-712. Il ne se
 * dessine que si un run est ouvert sur le projet (ADR-058) : le ticket en cours
 * et le rôle de l'agent qui travaille, ou « en attente » entre deux agents.
 */
export default function PosteDeFile({ projectId, run }: { projectId: string; run: RunDeSalle }) {
  const travaille = run.agent !== null;
  return (
    <div data-poste-de-file className="flex flex-col items-center gap-0.5 pb-1">
      <span className="text-xs font-medium text-blue-300">{run.ticketId ?? "Run en cours"}</span>
      <Agrandi>
        <AgentAuPupitre physique={physiqueDeProduit(projectId, "pipeline")} etat={travaille ? "actif" : "repos"} />
      </Agrandi>
      <span className="text-xs text-zinc-400">{run.agent === null ? "En attente" : nomDuRole(run.agent)}</span>
    </div>
  );
}
