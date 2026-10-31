import type { ReactNode } from "react";
import Modale from "../../design/ui/Modale";

interface FenetreProps {
  /** Identifie la fenêtre pour les lecteurs d'écran ; sert d'`id` au titre. */
  idTitre: string;
  /** Le bandeau, en capitales, comme celui des vues. */
  bandeau: string;
  children: ReactNode;
  pied: ReactNode;
}

/**
 * Fenêtre modale de la mise en ligne — maquette « carte et confirmation ».
 *
 * Elle est rendue sous la carte du projet : React fait remonter ses clics et
 * ses touches jusqu'à la carte, qui sélectionnerait le projet. `Modale` les
 * arrête (`isoler`). Elle ne se ferme ni par Escape ni par le fond : la
 * confirmation et le déroulé engagent des actions en ligne, qui se quittent
 * par un bouton du pied.
 */
export default function Fenetre({ idTitre, bandeau, children, pied }: FenetreProps) {
  return (
    <Modale isoler fond="bg-zinc-950/70" aria-labelledby={idTitre}>
      <div className="flex max-h-[85vh] w-[34rem] max-w-[92vw] cursor-default flex-col overflow-hidden rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl">
        <div className="flex h-10 shrink-0 items-center gap-2 border-b border-zinc-800 px-4 text-xs font-semibold uppercase tracking-wide">
          <span className="h-3.5 w-[3px] rounded-sm bg-violet-500" />
          {bandeau}
        </div>
        <div className="flex min-h-0 flex-col gap-3 overflow-y-auto p-4">{children}</div>
        <div className="flex shrink-0 justify-end gap-2 border-t border-zinc-800 px-4 py-3">
          {pied}
        </div>
      </div>
    </Modale>
  );
}
