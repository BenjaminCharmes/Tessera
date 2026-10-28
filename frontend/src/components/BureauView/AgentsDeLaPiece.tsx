import Agrandi from "../../design/bureau/Agrandi";
import AgentDebout from "../../design/bureau/AgentDebout";
import { libelleActivite, quiBavarde } from "../../lib/bureau/activites";
import type { AgentPlace } from "../../lib/bureau/activites";
import { nomDuPoste } from "../../lib/bureau/libelleDuPoste";
import { useEchelleDesSprites } from "../../hooks/useEchelleDesSprites";
import { ECHELLE_LARGE } from "../../lib/bureau/echelleDesSprites";
import { useEtirementDuSol, useMarcheActive } from "../../hooks/useEtirementDuSol";

interface AgentsDeLaPieceProps {
  projet: string;
  agents: readonly AgentPlace[];
}

/** Hauteur du pied de l'agent au-dessus du bas du sol : sous les postes, au niveau de leur nom. */
const BAS_DE_LA_RANGEE = 28;
/** Écart entre le sol des postes et celui du fond (machine, porte), en pixels. */
const DENIVELE_DU_FOND = 132;

/** Une petite bulle de conversation au-dessus de la tête : deux agents bavardent à la machine. */
function Bavardage() {
  return (
    <span
      data-bulle="bavardage"
      aria-hidden="true"
      className="anim-flotte absolute -top-5 left-1/2 -translate-x-1/2 rounded-full bg-zinc-200 px-1.5 text-mini font-medium leading-4 text-zinc-900"
    >
      …
    </span>
  );
}

function AgentMarcheur({ projet, agent, bavarde }: { projet: string; agent: AgentPlace; bavarde: boolean }) {
  const rendSaCopie = agent.activite === "copie";
  const monte = agent.niveau === "fond" ? -DENIVELE_DU_FOND : 0;
  // Les abscisses sont celles du repère de 800 px : étirées comme la grille des postes.
  const etirement = useEtirementDuSol();
  const marche = useMarcheActive();
  // Les décalages sont comptés pour l'échelle large : ils suivent l'échelle courante.
  const decalage = (agent.decalage * useEchelleDesSprites()) / ECHELLE_LARGE;
  const style = {
    bottom: BAS_DE_LA_RANGEE,
    transform: `translate(${agent.x * etirement + decalage}px, ${monte}px)`,
    opacity: agent.parti ? 0 : 1,
  };
  // Parti, l'agent n'est plus ni lu ni focalisable : il s'efface, il ne disparaît pas du DOM
  // pour pouvoir revenir à son poste au ticket suivant.
  const acces = agent.parti
    ? { "aria-hidden": true, inert: true, tabIndex: -1 }
    : {
        role: "img",
        "aria-label": `${nomDuPoste(agent.poste)}, ${libelleActivite(agent.activite ?? "tasse")}`,
      };
  return (
    <span
      data-agent={agent.poste}
      data-activite={agent.activite ?? "parti"}
      data-objet={rendSaCopie ? "feuille" : undefined}
      className={`${marche ? "marche " : ""}absolute left-0 z-10`}
      style={style}
      {...acces}
    >
      {bavarde && <Bavardage />}
      <Agrandi>
        <AgentDebout
          projet={projet}
          role={agent.poste}
          brasLeves={agent.activite === "fete"}
          sansTasse={agent.activite === "pause"}
          feuille={rendSaCopie}
        />
      </Agrandi>
    </span>
  );
}

/**
 * Les agents qui ont fini, posés en absolu sur le sol de la pièce : ils quittent
 * leur poste pour une activité, et partent tous par la porte quand le run se clôt.
 * La couche ne reçoit aucun clic : les postes dessous restent des boutons.
 */
export default function AgentsDeLaPiece({ projet, agents }: AgentsDeLaPieceProps) {
  const bavard = quiBavarde(agents);
  return (
    <div className="pointer-events-none absolute inset-0">
      {agents.map((agent) => (
        <AgentMarcheur key={agent.poste} projet={projet} agent={agent} bavarde={agent.poste === bavard} />
      ))}
    </div>
  );
}
