import RunHistorique from "../StatsView/RunHistorique";
import StatusPill from "../../design/ui/StatusPill";
import LienTicket from "../../design/ui/LienTicket";
import type { PipelineRun, Project, Ticket } from "../../types/api";
import CapturesDuRun from "./CapturesDuRun";
import {
  etatDuRun,
  formatCout,
  formatDate,
  formatDuree,
  libelleDeLEtat,
  libelleDesTours,
  lienPr,
  pastilleDuRun,
} from "./runs";

interface DetailDuRunProps {
  run: PipelineRun;
  /** Le ticket du run, quand il est encore dans la liste. */
  ticket: Ticket | null;
  project: Project | null;
}

function Chiffre({ libelle, valeur }: { libelle: string; valeur: string }) {
  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5">
      <div className="text-mini text-zinc-400">{libelle}</div>
      <div className="mt-0.5 text-lg font-semibold text-zinc-100">{valeur}</div>
    </div>
  );
}

function LienDeLaPr({ ticket, project }: { ticket: Ticket; project: Project | null }) {
  if (ticket.pr_number === null) return null;
  const href = lienPr(project?.github_remote ?? null, ticket.pr_number);
  const classes = "rounded-sm bg-zinc-800 px-2 py-0.5 text-xs text-zinc-200";
  if (href === null) return <span className={classes}>PR #{ticket.pr_number}</span>;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`${classes} hover:bg-zinc-700`}
    >
      PR #{ticket.pr_number}
    </a>
  );
}

/**
 * Detail of one run: who it was for, how it ended, the figures, then the
 * replayed thread of agents (ticket-427).
 */
export default function DetailDuRun({ run, ticket, project }: DetailDuRunProps) {
  const etat = etatDuRun(run);
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 px-8 pt-6">
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="font-mono text-xs text-zinc-400">
            <LienTicket projectId={project?.id ?? null} ticketId={run.ticket_id} /> · run du{" "}
            {formatDate(run.started_at)}
          </div>
          <h1 className="mt-1 text-xl font-semibold text-zinc-100">
            {ticket?.title ?? run.ticket_id}
          </h1>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <StatusPill
            etat={pastilleDuRun(run)}
            libelle={`${libelleDeLEtat(etat)}${etat !== "interrompu" && run.rounds !== null ? ` · ${libelleDesTours(run.rounds)}` : ""}`}
          />
          {ticket && <LienDeLaPr ticket={ticket} project={project} />}
        </div>
      </header>

      <div className="grid grid-cols-3 gap-2.5">
        <Chiffre libelle="Durée" valeur={formatDuree(run)} />
        <Chiffre libelle="Coût" valeur={formatCout(run.total_cost_usd)} />
        <Chiffre libelle="Tours" valeur={run.rounds === null ? "—" : String(run.rounds)} />
      </div>

      {run.arret && (
        <p className="rounded-sm border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-red-400">
          {run.arret}
        </p>
      )}

      <CapturesDuRun projectId={project?.id ?? null} ticketId={run.ticket_id} />

      <section className="flex min-h-0 flex-1 flex-col">
        <div className="mb-2 text-mini font-semibold uppercase tracking-wider text-zinc-500">
          Fil du run
        </div>
        <div className="min-h-0 flex-1 overflow-hidden rounded-md border border-zinc-800">
          <RunHistorique runId={run.id} ticketId={run.ticket_id} sansEntete />
        </div>
      </section>
    </div>
  );
}
