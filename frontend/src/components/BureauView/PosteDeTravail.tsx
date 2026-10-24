import Bulle from "../../design/bureau/Bulle";
import Poste from "../../design/bureau/Poste";
import { libelleDuPoste, nomDuPoste } from "../../lib/bureau/libelleDuPoste";
import type { PosteDuRun } from "../../lib/bureau/postesDuRun";
import type { SanteAgent } from "../../lib/santeAgent";

interface PosteDeTravailProps {
  poste: PosteDuRun;
  sante: SanteAgent;
}

/**
 * Un poste de la pièce, en bouton : son `aria-label` dit le poste et l'état en
 * mots. La bulle n'existe que sur un poste occupé (ADR-058).
 */
export default function PosteDeTravail({ poste, sante }: PosteDeTravailProps) {
  const occupe = poste.etat === "occupe";
  return (
    <div
      className={`flex flex-col items-center gap-1 pb-2 ${poste.etat === "libre" ? "opacity-50" : ""}`}
    >
      <div className="flex h-5 items-end">{occupe && <Bulle sante={sante} />}</div>
      <button
        type="button"
        aria-label={libelleDuPoste(poste.poste, poste.etat, sante)}
        className="cursor-pointer rounded-md p-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500"
      >
        <Poste etat={poste.etat} sante={sante} />
      </button>
      <span className="text-micro text-zinc-400">{nomDuPoste(poste.poste)}</span>
    </div>
  );
}
