import Bulle from "../../design/bureau/Bulle";
import Poste from "../../design/bureau/Poste";
import { libelleDuPoste, nomDuPoste } from "../../lib/bureau/libelleDuPoste";
import type { PosteDuRun } from "../../lib/bureau/postesDuRun";
import type { SanteAgent } from "../../lib/santeAgent";

interface PosteDeTravailProps {
  poste: PosteDuRun;
  sante: SanteAgent;
  /** Pièce sans run : pas de personnage, et le poste est « libre » plutôt qu'en attente. */
  auRepos?: boolean;
  /** Choisit l'agent au clic ; seul un poste occupé en a un (ticket-582). */
  onChoisir?: (poste: PosteDuRun["poste"]) => void;
}

/**
 * Un poste de la pièce, en bouton : son `aria-label` dit le poste et l'état en
 * mots. La bulle n'existe que sur un poste occupé qui ne travaille pas (ADR-058).
 * Seul un poste occupé agit au clic, et lui seul a le curseur main.
 */
export default function PosteDeTravail({
  poste,
  sante,
  auRepos = false,
  onChoisir,
}: PosteDeTravailProps) {
  const occupe = poste.etat === "occupe";
  const choisir = occupe && onChoisir ? () => onChoisir(poste.poste) : undefined;
  return (
    <div
      className={`flex flex-col items-center gap-1 pb-2 ${poste.etat === "libre" ? "opacity-50" : ""}`}
    >
      <div className="flex h-5 items-end">{occupe && <Bulle sante={sante} />}</div>
      <button
        type="button"
        aria-label={libelleDuPoste(poste.poste, poste.etat, sante, auRepos)}
        onClick={choisir}
        className={`rounded-md p-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 ${choisir ? "cursor-pointer" : ""}`}
      >
        <Poste etat={poste.etat} sante={sante} auRepos={auRepos} />
      </button>
      <span className="text-micro text-zinc-400">{nomDuPoste(poste.poste)}</span>
    </div>
  );
}
