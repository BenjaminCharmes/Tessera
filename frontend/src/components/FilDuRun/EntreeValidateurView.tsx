import { useState } from "react";
import { IconCheck, IconCross } from "../../design/icons";
import type { EntreeValidateur } from "../../hooks/streamState";
import EnteteVerdict from "./EnteteVerdict";

interface EntreeValidateurViewProps {
  entry: EntreeValidateur;
  isLast: boolean;
}

/** Résultat de la validation dans le fil du run, critère par critère. */
export default function EntreeValidateurView({
  entry,
  isLast,
}: EntreeValidateurViewProps) {
  const [expanded, setExpanded] = useState(false);
  const ouvert = isLast || expanded;
  const peutBasculer = !isLast;
  const approved = entry.verdict === "APPROVED";

  return (
    <div
      className="mx-3 mb-3 rounded-sm border border-zinc-700 overflow-hidden"
      data-testid="entree-pipeline"
    >
      <EnteteVerdict
        label="VALIDATEUR"
        approved={approved}
        verdictText={entry.verdict}
        peutBasculer={peutBasculer}
        ouvert={ouvert}
        onToggle={() => setExpanded((v) => !v)}
      />

      {ouvert && (
        <div className="p-3">
          {entry.feedback && (
            <p className="mb-2 text-xs text-zinc-400">{entry.feedback}</p>
          )}
          <ul className="space-y-1.5">
            {entry.criteria.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <span
                  className={`shrink-0 mt-0.5 ${c.passed ? "text-green-400" : "text-red-400"}`}
                >
                  {c.passed ? <IconCheck size={12} /> : <IconCross size={12} />}
                </span>
                <span>
                  <span
                    className={`font-medium ${c.passed ? "text-green-400" : "text-red-400"}`}
                  >
                    {c.criterion}
                  </span>
                  {c.note && (
                    <span className="ml-1 text-zinc-400">{c.note}</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
