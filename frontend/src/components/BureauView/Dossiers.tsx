import Dossier from "../../design/bureau/Dossier";
import type { StreamState } from "../../hooks/streamState";
import { useRestants } from "../../hooks/useRestants";
import { useTickets } from "../../hooks/useTickets";
import AvecInfobulle from "./AvecInfobulle";

interface DossiersProps {
  projet: string;
  runId: string | null;
  etat: StreamState;
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
      <ul>
        {visibles.map((ticket) => {
          const titre = titres.get(ticket);
          return <li key={ticket}>{titre ? `${ticket} — ${titre}` : ticket}</li>;
        })}
      </ul>
      {autres > 0 && <p className="text-zinc-400">{`et ${autres} autres`}</p>}
    </>
  );
}

/** La pile : un à trois dossiers empilés et le nombre écrit dessous (ADR-058). */
function Pile({ projet, restants }: PileProps) {
  const { tickets } = useTickets(projet);
  const titres = new Map(tickets.map((t) => [t.id, t.title]));

  return (
    <AvecInfobulle
      label={`Tickets restants : ${restants.length}`}
      className="flex flex-col items-center"
      infobulle={<ListeDesRestants restants={restants} titres={titres} />}
    >
      <div className="flex flex-col items-center">
        {Array.from({ length: hauteurDePile(restants.length) }, (_, i) => (
          <div key={i} className={i === 0 ? "" : "-mt-5"}>
            <Dossier />
          </div>
        ))}
      </div>
      <span aria-hidden="true" className="text-xs text-zinc-400">
        {`${restants.length} en file`}
      </span>
    </AvecInfobulle>
  );
}

/** Une seule pile pour la file, rien quand il n'en reste aucun ticket (ADR-058). */
export default function Dossiers({ projet, runId, etat }: DossiersProps) {
  const restants = useRestants(projet, runId, etat);
  if (restants.length === 0) return null;
  return <Pile projet={projet} restants={restants} />;
}
