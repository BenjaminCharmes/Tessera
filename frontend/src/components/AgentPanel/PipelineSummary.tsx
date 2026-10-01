import type { PipelineResult } from "../../types/api";
import { IconCheck, IconCross } from "../../design/icons";

interface LivraisonData {
  pr_number?: number;
  merged?: boolean;
  arret?: string;
}

interface PipelineSummaryProps {
  result: PipelineResult;
  durationMs?: number;
  /**
   * Vrai après `run_closed` : livraison et documentation sont terminées.
   * Entre `pipeline_done` et `run_closed`, un run approuvé affiche
   * « livraison en cours » plutôt que « Pipeline terminé » (ticket-267).
   * Défaut `true` pour rétrocompatibilité avec RunView.
   */
  runClosed?: boolean;
  /**
   * Ce que la livraison a produit, extrait de `livraison_done` (ticket-279).
   * Affiché après `runClosed` : numéro de PR, mergée ou cause d'arrêt.
   */
  livraisonData?: LivraisonData | null;
}

export default function PipelineSummary({
  result,
  durationMs,
  runClosed = true,
  livraisonData = null,
}: PipelineSummaryProps) {
  const durationStr = durationMs ? `${Math.round(durationMs / 1000)}s` : null;
  const titreApprouve = runClosed
    ? "Pipeline terminé"
    : "Revue terminée — livraison en cours";

  return (
    <div
      className={`mx-3 mb-3 rounded p-3 text-xs border ${
        result.approved
          ? "bg-green-900/30 border-green-700/50 text-green-300"
          : "bg-red-900/30 border-red-700/50 text-red-300"
      }`}
    >
      <div className="font-semibold">
        {result.approved ? (
          <>
            <IconCheck size={14} /> {titreApprouve}
          </>
        ) : (
          <>
            <IconCross size={14} /> Non approuvé
          </>
        )}
      </div>
      <div className="mt-1.5 space-y-0.5 text-zinc-400">
        <div>
          Ticket :{" "}
          <span className="text-zinc-300 font-mono">{result.ticket_id}</span>
        </div>
        <div>
          Rounds : <span className="text-zinc-300">{result.rounds}</span>
        </div>
        <div>
          Statut : <span className="text-zinc-300">{result.final_status}</span>
        </div>
        {durationStr && (
          <div>
            Durée : <span className="text-zinc-300">{durationStr}</span>
          </div>
        )}
        {runClosed && livraisonData && (
          <div>
            Livraison :{" "}
            <span className="text-zinc-300">
              {livraisonData.merged
                ? `PR #${livraisonData.pr_number ?? "?"} mergée`
                : livraisonData.arret !== undefined
                  ? livraisonData.arret
                  : livraisonData.pr_number !== undefined
                    ? `PR #${livraisonData.pr_number} ouverte`
                    : "terminée"}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
