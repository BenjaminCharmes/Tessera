import type { EntreeAnomalie } from "../../hooks/streamState";
import { libelleDeRegle } from "../../lib/anomalies";

interface EntreeAnomalieViewProps {
  entry: EntreeAnomalie;
}

/**
 * Une anomalie relevée par le détecteur, dans le fil du run (ticket-840, ADR-078).
 *
 * Ambre, car c'est une attente à vérifier et non un échec (ADR-026) ; jamais de
 * violet en texte. Le message nomme l'outil, jamais son contenu.
 */
export default function EntreeAnomalieView({ entry }: EntreeAnomalieViewProps) {
  return (
    <div
      className="mx-3 mb-3 overflow-hidden rounded-sm border border-amber-700"
      data-testid="entree-anomalie"
    >
      <div className="flex items-center gap-2 bg-amber-950/40 px-3 py-1.5 text-xs">
        <span className="font-semibold text-amber-300">ANOMALIE</span>
        <span className="text-amber-300">{libelleDeRegle(entry.regle)}</span>
      </div>
      <p className="px-3 py-2 text-xs text-amber-200">{entry.message}</p>
    </div>
  );
}
