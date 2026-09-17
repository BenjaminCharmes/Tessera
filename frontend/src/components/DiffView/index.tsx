import { useEffect, useState } from "react";
import MonacoEditor from "@monaco-editor/react";
import { api } from "../../lib/api";
import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
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
 */
interface DiffViewProps {
  projectId: string;
  ticketId: string;
}

export default function DiffView({ projectId, ticketId }: DiffViewProps) {
  const [resultat, setResultat] = useState<TicketDiff | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    let annule = false;
    setResultat(null);
    setErreur(null);
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

      {resultat?.files.length ? (
        <ul className="flex flex-wrap gap-1.5 border-b border-zinc-800 px-4 py-2">
          {resultat.files.map((f) => (
            <li
              key={f}
              className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-micro text-zinc-300"
            >
              {f}
            </li>
          ))}
        </ul>
      ) : null}

      {resultat?.diff ? (
        <div className="min-h-0 flex-1">
          <MonacoEditor
            height="100%"
            theme="vs-dark"
            language="diff"
            value={resultat.diff}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              wordWrap: "on",
              fontSize: 13,
              scrollBeyondLastLine: false,
              padding: { top: 12 },
            }}
          />
        </div>
      ) : null}
    </div>
  );
}
