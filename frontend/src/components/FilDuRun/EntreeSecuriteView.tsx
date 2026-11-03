import { useState } from "react";
import type { EntreeSecurite } from "../../hooks/streamState";
import EnteteVerdict from "./EnteteVerdict";

interface EntreeSecuriteViewProps {
  entry: EntreeSecurite;
  isLast: boolean;
}

/** Résultat de l'audit de sécurité dans le fil du run. */
export default function EntreeSecuriteView({
  entry,
  isLast,
}: EntreeSecuriteViewProps) {
  const [expanded, setExpanded] = useState(false);
  const ouvert = isLast || expanded;
  const peutBasculer = !isLast;
  const approved = entry.verdict !== "BLOCK";

  return (
    <div
      className="mx-3 mb-3 rounded-sm border border-zinc-700 overflow-hidden"
      data-testid="entree-pipeline"
    >
      <EnteteVerdict
        label="SÉCURITÉ"
        approved={approved}
        verdictText={entry.verdict}
        peutBasculer={peutBasculer}
        ouvert={ouvert}
        onToggle={() => setExpanded((v) => !v)}
      />

      {ouvert && entry.summary && (
        <div className="p-3 text-xs text-zinc-400">{entry.summary}</div>
      )}
    </div>
  );
}
