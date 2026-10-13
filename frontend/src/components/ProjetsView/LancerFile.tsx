import { useState } from "react";
import { api } from "../../lib/api";
import type { ProjectOverview } from "../../types/api";
import { idsAFaire } from "./idsAFaire";

interface LancerFileProps {
  projet: ProjectOverview;
  /** Appelé une fois la file partie : la vue relit la vue d'ensemble. */
  onLancee: () => void;
}

function messageDEchec(e: unknown): string {
  const texte = e instanceof Error ? e.message : "";
  if (texte.startsWith("API 409")) return "Un run est déjà en cours sur ce projet.";
  return texte || "Lancement impossible.";
}

const BOUTON = "rounded-sm px-2 py-0.5 text-micro";

/**
 * Lance la file des tickets « à faire » d'un projet depuis sa carte — ticket-412.
 *
 * La confirmation se fait sur place, sans fenêtre modale. Tout clic ici
 * s'arrête : la carte n'est pas sélectionnée.
 */
export default function LancerFile({ projet, onLancee }: LancerFileProps) {
  const [confirmation, setConfirmation] = useState(false);
  const [enCours, setEnCours] = useState(false);
  const [echec, setEchec] = useState<string | null>(null);
  const n = projet.tickets.todo;

  async function lancer() {
    setEnCours(true);
    setEchec(null);
    try {
      const { tickets } = await api.tickets.list(projet.id);
      await api.orchestrator.run({
        project_id: projet.id,
        mode: "queue",
        ticket_ids: idsAFaire(tickets),
      });
      setConfirmation(false);
      onLancee();
    } catch (e) {
      setEchec(messageDEchec(e));
    } finally {
      setEnCours(false);
    }
  }

  if (n <= 0) return null;
  return (
    <div
      className="flex flex-wrap items-center gap-2"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      {confirmation ? (
        <>
          <span className="text-micro text-zinc-300">Lancer {n} tickets ?</span>
          <button
            type="button"
            disabled={enCours}
            onClick={() => void lancer()}
            className={`${BOUTON} bg-violet-600 text-white hover:bg-violet-500 disabled:opacity-50`}
          >
            Lancer
          </button>
          <button
            type="button"
            disabled={enCours}
            onClick={() => setConfirmation(false)}
            className={`${BOUTON} bg-zinc-700 text-zinc-200 hover:bg-zinc-600`}
          >
            Annuler
          </button>
        </>
      ) : (
        <button
          type="button"
          disabled={projet.run_actif}
          title={projet.run_actif ? "Un run est en cours" : undefined}
          onClick={() => setConfirmation(true)}
          className={`${BOUTON} bg-zinc-700 text-zinc-200 hover:bg-zinc-600 disabled:cursor-not-allowed disabled:opacity-50`}
        >
          File ({n})
        </button>
      )}
      {echec && (
        <span role="alert" className="text-micro text-red-400">
          {echec}
        </span>
      )}
    </div>
  );
}
