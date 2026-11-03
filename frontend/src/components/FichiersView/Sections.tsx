import { cheminAbsolu, cheminRelatif } from "../../lib/indexFichiers";
import type { FichierDiff } from "../DiffView/parse";

const TITRE = "mb-2 text-mini uppercase tracking-wider text-zinc-500";
const LIGNE =
  "flex w-full items-center justify-between gap-3 text-left font-mono text-xs transition-colors";

interface ResultatsProps {
  racine: string;
  chemins: string[];
  onOpen: (chemin: string) => void;
}

/** Les fichiers qui correspondent à la recherche. */
export function Resultats({ racine, chemins, onOpen }: ResultatsProps) {
  if (chemins.length === 0) {
    return <p className="text-xs text-zinc-500">Aucun fichier ne correspond.</p>;
  }
  return (
    <ul aria-label="Résultats de la recherche" className="flex flex-col">
      {chemins.map((chemin) => (
        <li key={chemin}>
          <button
            type="button"
            onClick={() => onOpen(chemin)}
            className={`${LIGNE} px-1 py-1.5 text-zinc-300 hover:bg-zinc-800`}
          >
            {cheminRelatif(racine, chemin)}
          </button>
        </li>
      ))}
    </ul>
  );
}

interface TouchesProps {
  racine: string;
  ticketId: string | null;
  fichiers: FichierDiff[];
  erreur: string | null;
  onOpen: (chemin: string) => void;
}

/** Les fichiers qu'un run a touchés, avec ses lignes ajoutées et retirées. */
export function SectionTouches({
  racine,
  ticketId,
  fichiers,
  erreur,
  onOpen,
}: TouchesProps) {
  return (
    <section aria-label="Touchés par le dernier run">
      <h2 className={TITRE}>
        Touchés par le dernier run{ticketId ? ` — ${ticketId}` : ""}
      </h2>
      {ticketId === null && (
        <p className="text-xs text-zinc-500">Aucun ticket terminé pour l'instant.</p>
      )}
      {erreur && <p className="text-xs text-red-400">Diff indisponible : {erreur}</p>}
      {fichiers.length > 0 && (
        <ul className="overflow-hidden rounded-md border border-zinc-800">
          {fichiers.map((f) => (
            <li key={f.chemin} className="border-b border-zinc-800 last:border-b-0">
              <button
                type="button"
                onClick={() => onOpen(cheminAbsolu(racine, f.chemin))}
                className={`${LIGNE} px-3 py-2 text-zinc-200 hover:bg-zinc-800`}
              >
                <span className="truncate">{f.chemin}</span>
                <span className="shrink-0">
                  <span className="text-green-400">+{f.ajouts}</span>{" "}
                  <span className="text-red-400">-{f.retraits}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

interface RecentsProps {
  racine: string;
  chemins: string[];
  onOpen: (chemin: string) => void;
}

/** Les derniers fichiers ouverts dans ce projet. */
export function SectionRecents({ racine, chemins, onOpen }: RecentsProps) {
  return (
    <section aria-label="Ouverts récemment">
      <h2 className={TITRE}>Ouverts récemment</h2>
      {chemins.length === 0 ? (
        <p className="text-xs text-zinc-500">Aucun fichier ouvert dans ce projet.</p>
      ) : (
        <ul className="flex flex-col">
          {chemins.map((chemin) => (
            <li key={chemin}>
              <button
                type="button"
                onClick={() => onOpen(chemin)}
                className={`${LIGNE} px-1 py-1.5 text-zinc-300 hover:bg-zinc-800`}
              >
                {cheminRelatif(racine, chemin)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
