import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import Dossier from "../../design/bureau/Dossier";
import type { StreamState } from "../../hooks/streamState";
import { useRestants } from "../../hooks/useRestants";
import { useTickets } from "../../hooks/useTickets";
import { positionInfobulle } from "../../lib/bureau/positionInfobulle";
import type { PositionFixe, Rectangle } from "../../lib/bureau/positionInfobulle";

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

interface InfobulleProps {
  id: string;
  ancre: Rectangle;
  restants: readonly string[];
  titres: Map<string, string>;
}

/**
 * Les tickets restants avec leur titre ; un titre introuvable laisse l'identifiant seul.
 * Rendue dans `document.body` : la pièce coupe ce qui déborde (`overflow-hidden`).
 */
function Infobulle({ id, ancre, restants, titres }: InfobulleProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<PositionFixe>({ top: ancre.top, left: ancre.left });
  const visibles = restants.slice(0, LIGNES_MAX);
  const autres = restants.length - visibles.length;

  // Mesurée avant la peinture : la position finale dépend de la taille réelle de l'infobulle.
  useLayoutEffect(() => {
    const boite = ref.current;
    if (!boite) return;
    const mesure = { largeur: boite.offsetWidth, hauteur: boite.offsetHeight };
    setPosition(positionInfobulle(ancre, mesure, { largeur: window.innerWidth, hauteur: window.innerHeight }));
  }, [ancre, restants, titres]);

  return createPortal(
    <div
      id={id}
      ref={ref}
      role="tooltip"
      style={{ top: position.top, left: position.left }}
      className="pointer-events-none fixed z-50 w-max max-w-72 rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-200"
    >
      <ul>
        {visibles.map((ticket) => {
          const titre = titres.get(ticket);
          return <li key={ticket}>{titre ? `${ticket} — ${titre}` : ticket}</li>;
        })}
      </ul>
      {autres > 0 && <p className="text-zinc-400">{`et ${autres} autres`}</p>}
    </div>,
    document.body,
  );
}

/** La pile : un à trois dossiers empilés et le nombre écrit dessous (ADR-058). */
function Pile({ projet, restants }: PileProps) {
  // L'ancre est le rectangle de la pile à l'ouverture : l'infobulle, hors de la pièce, se place dessus.
  const [ancre, setAncre] = useState<Rectangle | null>(null);
  const racine = useRef<HTMLDivElement>(null);
  const { tickets } = useTickets(projet);
  const titres = new Map(tickets.map((t) => [t.id, t.title]));
  const idInfobulle = useId();
  const ouvrir = () => setAncre(racine.current?.getBoundingClientRect() ?? null);
  const fermer = () => setAncre(null);

  // Une position fixe ne suit pas le défilement : l'infobulle se referme plutôt que de rester à côté.
  useEffect(() => {
    if (ancre === null) return;
    const refermer = () => setAncre(null);
    window.addEventListener("scroll", refermer, true);
    return () => window.removeEventListener("scroll", refermer, true);
  }, [ancre]);

  return (
    <div
      ref={racine}
      role="group"
      tabIndex={0}
      aria-label={`Tickets restants : ${restants.length}`}
      aria-describedby={ancre ? idInfobulle : undefined}
      className="flex flex-col items-center"
      onMouseEnter={ouvrir}
      onMouseLeave={fermer}
      onFocus={ouvrir}
      onBlur={fermer}
    >
      {ancre && <Infobulle id={idInfobulle} ancre={ancre} restants={restants} titres={titres} />}
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
    </div>
  );
}

/** Une seule pile pour la file, rien quand il n'en reste aucun ticket (ADR-058). */
export default function Dossiers({ projet, runId, etat }: DossiersProps) {
  const restants = useRestants(projet, runId, etat);
  if (restants.length === 0) return null;
  return <Pile projet={projet} restants={restants} />;
}
