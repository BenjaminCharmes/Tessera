import { useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";
import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import { decouperDiff } from "./parse";
import type { TicketDiff } from "../../types/api";

/**
 * Ce qu'un run a produit, lisible sans quitter l'IDE (ticket-069).
 *
 * Le pipeline relit le diff git réel depuis ADR-018, mais rien ne l'exposait :
 * pour juger un run il fallait ouvrir VSCode et taper `git diff`. Le 2026-09-17,
 * deux tickets se sont affichés `done` sans avoir rien commité, et rien à
 * l'écran ne permettait de le voir.
 *
 * D'où la distinction, ici, entre trois états qu'on aurait tort de confondre :
 * un ticket jamais lancé, une branche qui existe mais ne contient rien, et un
 * diff réel.
 *
 * **Un fichier à la fois.** Le premier jet versait tout le diff dans Monaco :
 * cinq fichiers concaténés, ajouts et retraits de la même couleur, et rien
 * pour naviguer. Sur un run qui touche deux Markdown de plusieurs centaines de
 * lignes, on ne lit rien. On choisit donc un fichier, et chaque ligne est
 * peinte selon son rôle (ticket-075).
 */
interface DiffViewProps {
  projectId: string;
  ticketId: string;
}

export default function DiffView({ projectId, ticketId }: DiffViewProps) {
  const [resultat, setResultat] = useState<TicketDiff | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [actif, setActif] = useState(0);

  const fichiers = useMemo(
    () => decouperDiff(resultat?.diff ?? ""),
    [resultat?.diff],
  );
  const fichier = fichiers[actif];

  useEffect(() => {
    let annule = false;
    setResultat(null);
    setErreur(null);
    setActif(0);
    void (async () => {
      try {
        const d = await api.tickets.diff(projectId, ticketId);
        if (!annule) setResultat(d);
      } catch (err: unknown) {
        if (!annule) setErreur(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      annule = true;
    };
  }, [projectId, ticketId]);

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-2 border-b border-zinc-700 px-4`}>
        <RegionTitle>Diff du ticket</RegionTitle>
        {resultat?.branch && (
          <span className="truncate font-mono text-mini text-zinc-500">
            {resultat.branch}
          </span>
        )}
      </div>

      {erreur && (
        <p className="px-4 py-3 text-xs text-red-400">
          Diff indisponible : {erreur}
        </p>
      )}

      {resultat && !erreur && resultat.branch === null && (
        <p className="px-4 py-3 text-xs text-zinc-500">
          Ce ticket n'a jamais été lancé — aucune branche ne lui correspond.
        </p>
      )}

      {resultat && !erreur && resultat.branch !== null && !resultat.diff && (
        <p className="px-4 py-3 text-xs text-amber-300">
          La branche existe mais n'a rien produit : le run n'a rien commité.
        </p>
      )}

      {fichiers.length > 0 && (
        <ul className="flex shrink-0 flex-wrap gap-1 border-b border-zinc-800 px-4 py-2">
          {fichiers.map((f, i) => (
            <li key={f.chemin}>
              <button
                type="button"
                onClick={() => setActif(i)}
                className={`flex items-center gap-1.5 rounded px-2 py-1 font-mono text-micro transition-colors ${
                  i === actif
                    ? "bg-violet-500/15 text-violet-200 ring-1 ring-inset ring-violet-500/40"
                    : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {f.chemin}
                <span className="text-green-400">+{f.ajouts}</span>
                <span className="text-red-400">-{f.retraits}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {fichier && (
        <div className="min-h-0 flex-1 overflow-auto bg-zinc-950 font-mono text-micro leading-relaxed">
          {fichier.lignes.map((ligne, i) => (
            <div
              key={i}
              className={`whitespace-pre-wrap break-all px-4 ${
                ligne.type === "ajout"
                  ? "bg-green-950/40 text-green-300"
                  : ligne.type === "retrait"
                    ? "bg-red-950/40 text-red-300"
                    : ligne.type === "hunk"
                      ? "mt-2 bg-zinc-900 py-0.5 text-violet-300"
                      : "text-zinc-400"
              }`}
            >
              {ligne.texte || " "}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
