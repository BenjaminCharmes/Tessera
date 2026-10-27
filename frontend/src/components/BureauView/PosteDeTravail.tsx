import Agrandi from "../../design/bureau/Agrandi";
import Bulle from "../../design/bureau/Bulle";
import BulleDOutil from "../../design/bureau/BulleDOutil";
import Poste from "../../design/bureau/Poste";
import { libelleDuPoste, nomDuPoste } from "../../lib/bureau/libelleDuPoste";
import type { PosteDuRun } from "../../lib/bureau/postesDuRun";
import type { SanteAgent } from "../../lib/santeAgent";

interface PosteDeTravailProps {
  /** Le projet de la pièce : il donne à chaque agent son physique. */
  projet: string;
  poste: PosteDuRun;
  sante: SanteAgent;
  /** Pièce sans run : pas de personnage, et le poste est « libre » plutôt qu'en attente. */
  auRepos?: boolean;
  /** Run clos : les agents sont partis, aucun ne reste assis. */
  parti?: boolean;
  /** L'agent est chez le directeur ou aux RH : le poste reste, sa chaise est vide (ticket-597). */
  absent?: boolean;
  /** Choisit l'agent au clic ; seul un poste occupé en a un (ticket-582). */
  onChoisir?: (poste: PosteDuRun["poste"]) => void;
  /** Ce que l'agent fait, en une ligne, dans les dix secondes d'un appel d'outil (ticket-601). */
  outil?: string | null;
}

/**
 * Un poste de la pièce, en bouton : son `aria-label` dit le poste et l'état en
 * mots. La bulle de santé n'existe que sur un poste occupé qui ne travaille pas ;
 * celui qui travaille porte, dix secondes après un appel d'outil, ce qu'il fait (ADR-058).
 * Seul un poste occupé agit au clic, et lui seul a le curseur main.
 */
export default function PosteDeTravail({
  projet,
  poste,
  sante,
  auRepos = false,
  parti = false,
  absent = false,
  onChoisir,
  outil = null,
}: PosteDeTravailProps) {
  const occupe = poste.etat === "occupe";
  const choisir = occupe && onChoisir ? () => onChoisir(poste.poste) : undefined;
  // L'agent qui a fini se lève : la pièce le dessine hors du poste (AgentsDeLaPiece).
  return (
    <div
      data-absent={absent}
      className={`flex flex-col items-center gap-1 pb-2 ${poste.etat === "libre" ? "opacity-50" : ""}`}
    >
      {/* La bulle suit l'agent : absent, c'est la salle où il est qui la porte. */}
      <div className="flex h-5 max-w-full items-end">
        {occupe && !absent && <Bulle sante={sante} />}
        {occupe && !absent && sante === "actif" && outil && <BulleDOutil phrase={outil} />}
      </div>
      <button
        type="button"
        aria-label={libelleDuPoste(poste.poste, poste.etat, sante, auRepos)}
        onClick={choisir}
        tabIndex={absent ? -1 : undefined}
        className={`relative rounded-md p-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500 ${choisir ? "cursor-pointer" : ""}`}
      >
        <Agrandi>
          <Poste
            projet={projet}
          role={poste.poste}
          etat={poste.etat}
          sante={sante}
          auRepos={auRepos}
            parti={parti || absent}
          />
        </Agrandi>
      </button>
      <span className="text-micro text-zinc-400">{nomDuPoste(poste.poste)}</span>
    </div>
  );
}
