import type { ReactNode } from "react";
import Plante from "../../design/bureau/Plante";
import { IconInfo } from "../../design/icons";

interface SalleProps {
  titre: string;
  /** Ce que la salle accueille : une phrase, en infobulle sur le titre (marque d'info), jamais écrite sous lui. */
  entete: string;
  /** Ce que dit la salle quand personne n'y est. */
  vide: string;
  /** Le mobilier : la salle elle-même, dessiné occupée ou non (ADR-058). */
  mobilier: ReactNode;
  /** Contour ambre : quelqu'un ou quelque chose attend (une question, un repli). */
  ambre?: boolean;
  /** Les occupants : une salle sans enfant dit `vide`. */
  children?: ReactNode[];
}

/** Le cadre commun des salles : titre fin, sol de 156 px et mobilier toujours là, occupants à côté, une plante dans le coin. */
export default function Salle({ titre, entete, vide, mobilier, ambre = false, children = [] }: SalleProps) {
  const occupee = children.length > 0;
  const contour = ambre ? "border-amber-900" : "border-zinc-800";
  return (
    <aside
      aria-label={titre}
      data-occupee={occupee}
      data-sol="lames"
      data-contour={ambre ? "amber" : "neutre"}
      className={`sol-lames min-w-0 flex-1 rounded-lg border px-3 py-[5px] ${contour}`}
    >
      <h3 title={entete} className="flex items-center gap-1 text-micro uppercase tracking-wide text-zinc-500">
        {titre}
        <IconInfo size={12} data-marque="info" />
      </h3>
      <div className="flex min-h-39 items-end justify-between gap-4 px-1 py-2">
        <div className="flex min-w-0 items-center gap-4">
          <div className="shrink-0">{mobilier}</div>
          {occupee && <ul className="flex min-w-0 flex-col gap-1">{children}</ul>}
        </div>
        <Plante />
      </div>
      {!occupee && <p className="mb-1 text-xs text-zinc-500">{vide}</p>}
    </aside>
  );
}
