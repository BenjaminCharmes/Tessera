import AgentDebout from "../../design/bureau/AgentDebout";
import { libelleActivite } from "../../lib/bureau/activites";
import type { AgentPlace } from "../../lib/bureau/activites";
import { nomDuPoste } from "../../lib/bureau/libelleDuPoste";

interface AgentsDeLaPieceProps {
  projet: string;
  agents: readonly AgentPlace[];
}

/** Hauteur du pied de l'agent au-dessus du bas du sol : sous les postes, au niveau de leur nom. */
const BAS_DE_LA_RANGEE = 28;
/** Écart entre le sol des postes et celui du fond (machine, porte), en pixels. */
const DENIVELE_DU_FOND = 104;

function AgentMarcheur({ projet, agent }: { projet: string; agent: AgentPlace }) {
  const monte = agent.niveau === "fond" ? -DENIVELE_DU_FOND : 0;
  const style = {
    bottom: BAS_DE_LA_RANGEE,
    transform: `translate(${agent.x}px, ${monte}px)`,
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
      className="marche absolute left-0 z-10"
      style={style}
      {...acces}
    >
      <AgentDebout projet={projet} role={agent.poste} etire={agent.activite === "etire" || agent.activite === "fete"} />
    </span>
  );
}

/**
 * Les agents qui ont fini, posés en absolu sur le sol de la pièce : ils quittent
 * leur poste pour une activité, et partent tous par la porte quand le run se clôt.
 * La couche ne reçoit aucun clic : les postes dessous restent des boutons.
 */
export default function AgentsDeLaPiece({ projet, agents }: AgentsDeLaPieceProps) {
  return (
    <div className="pointer-events-none absolute inset-0">
      {agents.map((agent) => (
        <AgentMarcheur key={agent.poste} projet={projet} agent={agent} />
      ))}
    </div>
  );
}
