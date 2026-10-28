import Agrandi from "../../design/bureau/Agrandi";
import Dossier from "../../design/bureau/Dossier";
import type { StreamState } from "../../hooks/streamState";
import { useRestants } from "../../hooks/useRestants";
import { useTickets } from "../../hooks/useTickets";
import AvecInfobulle from "./AvecInfobulle";

interface DossiersProps {
  projet: string;
  runId: string | null;
  etat: StreamState;
  /**
   * Ouvre l'onglet Tickets du projet : des dossiers mènent aux tickets, le fil a
   * déjà son bouton (ticket-622). Sans lui, la pile n'est qu'un objet.
   */
  onActiver?: () => void;
}

/** Hauteur maximale de la pile dessinée, et nombre de lignes de l'infobulle. */
const DOSSIERS_MAX = 3;
const LIGNES_MAX = 10;

/** Nombre de dossiers dessinés : un par ticket jusqu'à trois, trois au-delà. */
function hauteurDePile(restants: number): number {
  return Math.min(Math.max(restants, 1), DOSSIERS_MAX);
}

interface PileProps {
  projet: string;
  restants: readonly string[];
  onActiver?: () => void;
}

interface ListeProps {
  restants: readonly string[];
  titres: Map<string, string>;
}

/** Les tickets restants avec leur titre ; un titre introuvable laisse l'identifiant seul. */
function ListeDesRestants({ restants, titres }: ListeProps) {
  const visibles = restants.slice(0, LIGNES_MAX);
  const autres = restants.length - visibles.length;
  return (
    <>
      <ul className="flex flex-col gap-1.5 py-0.5">
        {visibles.map((ticket) => {
          const titre = titres.get(ticket);
          return (
            <li key={ticket} className="flex gap-2 leading-snug">
              <span
                aria-hidden="true"
                className="mt-1.5 size-1.5 shrink-0 rounded-full bg-zinc-500"
              />
              <span>
                <code className="font-mono text-zinc-100">{ticket}</code>
                {titre && (
                  <span className="text-zinc-300">{` — ${titre}`}</span>
                )}
              </span>
            </li>
          );
        })}
      </ul>
      {autres > 0 && <p className="text-zinc-400">{`et ${autres} autres`}</p>}
    </>
  );
}

/** La pile : un à trois dossiers empilés, le nombre sur une pastille, la liste en infobulle (ADR-058). */
function Pile({ projet, restants, onActiver }: PileProps) {
  const { tickets } = useTickets(projet);
  const titres = new Map(tickets.map((t) => [t.id, t.title]));

  return (
    <AvecInfobulle
      label={`Tickets restants : ${restants.length}`}
      className="relative flex flex-col items-center"
      large
      onActiver={onActiver}
      infobulle={<ListeDesRestants restants={restants} titres={titres} />}
    >
      <Agrandi>
        <div className="flex flex-col items-center">
          {Array.from({ length: hauteurDePile(restants.length) }, (_, i) => (
            <div key={i} className={i === 0 ? "" : "-mt-5"}>
              <Dossier />
            </div>
          ))}
        </div>
      </Agrandi>
      <span
        aria-hidden="true"
        data-badge="restants"
        className="absolute -right-2 -top-2 min-w-4 rounded-full bg-zinc-700 px-1 text-center text-micro leading-4 text-zinc-100"
      >
        {restants.length}
      </span>
    </AvecInfobulle>
  );
}

/** Une seule pile pour la file, rien quand il n'en reste aucun ticket (ADR-058). */
export default function Dossiers({
  projet,
  runId,
  etat,
  onActiver,
}: DossiersProps) {
  const restants = useRestants(projet, runId, etat);
  if (restants.length === 0) return null;
  return <Pile projet={projet} restants={restants} onActiver={onActiver} />;
}
