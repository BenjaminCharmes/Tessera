import { useState } from "react";
import { IconChevronDown, IconChevronRight } from "../../design/icons";
import PanneauPipeline from "./PanneauPipeline";

/**
 * Le réglage du pipeline, replié, au-dessus des onglets qui s'en servent —
 * ticket-441.
 *
 * Il vivait sous l'en-tête du projet, donc dans chaque onglet, alors qu'il ne
 * sert qu'à lire les agents ou à lancer un ticket.
 */
interface SectionPipelineProps {
  projectId: string;
  /** Un run tourne sur ce projet : le pipeline se règle en lecture seule (ticket-196). */
  runEnCours: boolean;
}

export default function SectionPipeline({
  projectId,
  runEnCours,
}: SectionPipelineProps) {
  const [ouvert, setOuvert] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOuvert((v) => !v)}
        aria-expanded={ouvert}
        className="flex w-full items-center gap-1.5 px-3 py-1 text-left text-mini text-zinc-500 hover:text-zinc-300"
      >
        {/* Sans chevron, ce libellé gris ne se lisait pas comme un bouton
            (ticket-205). Même affordance que les listes repliables du chat. */}
        {ouvert ? (
          <IconChevronDown size={12} />
        ) : (
          <IconChevronRight size={12} />
        )}
        Pipeline
      </button>
      {ouvert ? (
        <PanneauPipeline projectId={projectId} runEnCours={runEnCours} />
      ) : null}
    </>
  );
}
