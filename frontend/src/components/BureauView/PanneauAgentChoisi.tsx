import Button from "../../design/ui/Button";
import type { StreamState } from "../../hooks/streamState";
import { lignesDeLAgent } from "../../lib/bureau/agentChoisi";
import type { PosteId } from "../../lib/bureau/postesDuRun";
import type { RunActif } from "../../types/api";

export interface AgentChoisi {
  projet: string;
  poste: PosteId;
}

interface PanneauAgentChoisiProps {
  choix: AgentChoisi | null;
  /** L'état et le run du projet choisi : sans état, le panneau reste vide. */
  etat?: StreamState;
  run?: RunActif;
  /** L'horloge du Bureau : le panneau n'ouvre aucun minuteur. */
  maintenant: number;
  /** Ouvre le fil du run, comme le bouton « Fil » de la pièce. */
  onOuvrir?: (runId: string) => void;
}

/**
 * Le panneau sous « À toi » : ce que l'état du run dit de l'agent choisi. Lignes
 * dérivées à chaque rendu : un agent qui ne travaille plus retombe sur l'invite.
 * Pas de « Lui écrire » : le canal d'écriture n'est pas câblé dans le Bureau.
 */
export default function PanneauAgentChoisi({ choix, etat, run, maintenant, onOuvrir }: PanneauAgentChoisiProps) {
  const lignes = choix && etat ? lignesDeLAgent(choix.projet, choix.poste, etat, maintenant, run) : null;

  return (
    <aside
      aria-label="Agent choisi"
      className="flex flex-col gap-2 rounded-lg border border-zinc-800 bg-zinc-900 p-3"
    >
      <h3 className="text-corps font-semibold text-zinc-200">Agent choisi</h3>
      {lignes === null ? (
        <p className="text-micro text-zinc-500">Clique un agent au travail</p>
      ) : (
        <dl className="flex flex-col gap-1">
          {lignes.map(({ libelle, valeur }) => (
            <div key={libelle} className="flex flex-col">
              <dt className="text-micro uppercase tracking-wide text-zinc-500">{libelle}</dt>
              <dd className="text-xs text-zinc-200">{valeur}</dd>
            </div>
          ))}
        </dl>
      )}
      {lignes !== null && run && onOuvrir && (
        <Button taille="compact" onClick={() => onOuvrir(run.run_id)}>
          Suivre le fil
        </Button>
      )}
    </aside>
  );
}
