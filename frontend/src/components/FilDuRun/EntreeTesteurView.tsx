import { useState } from "react";
import type { EntreeTesteur } from "../../hooks/streamState";
import EnteteVerdict from "./EnteteVerdict";

interface EntreeTesteurViewProps {
  entry: EntreeTesteur;
  isLast: boolean;
}

/**
 * Une entrée du testeur dans le fil — repliable quand terminée et non-dernière.
 *
 * En rouge, elle dit que le run repart au codeur sans passer par la revue
 * (ticket-321).
 */
export default function EntreeTesteurView({
  entry,
  isLast,
}: EntreeTesteurViewProps) {
  const [expanded, setExpanded] = useState(false);
  const ouvert = isLast || expanded;
  const peutBasculer = !isLast;
  const verdictText = entry.passed
    ? "tests ok"
    : "retour au codeur, sans revue";

  return (
    <div
      className="mx-3 mb-3 rounded-sm border border-zinc-700 overflow-hidden"
      data-testid="entree-pipeline"
    >
      <EnteteVerdict
        label="TESTEUR"
        approved={entry.passed}
        verdictText={verdictText}
        peutBasculer={peutBasculer}
        ouvert={ouvert}
        onToggle={() => setExpanded((v) => !v)}
      />

      {ouvert && (
        <div className="p-3">
          <p className="mb-2 text-xs text-zinc-400">{entry.output_summary}</p>
          {!entry.passed && entry.errors.length > 0 && (
            <ul className="space-y-1">
              {entry.errors.map((err, i) => (
                <li key={i} className="font-mono text-xs text-red-400">
                  {err}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
