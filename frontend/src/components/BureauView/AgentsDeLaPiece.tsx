import Agrandi from "../../design/bureau/Agrandi";
import type { MotifDeVisite } from "../../lib/bureau/ronde";
import AgentDebout from "../../design/bureau/AgentDebout";
import { libelleActivite, quiBavarde } from "../../lib/bureau/activites";
import type { AgentPlace, Placement } from "../../lib/bureau/activites";
import { nomDuPoste } from "../../lib/bureau/libelleDuPoste";
import { avecLeNom } from "../../lib/bureau/noms";
import type { PosteId, RoleAffiche } from "../../lib/bureau/postesDuRun";
import type { RedacteurPlace } from "../../lib/bureau/redaction";
import DirecteurEnVisite from "./DirecteurEnVisite";
import { useEchelleDesSprites } from "../../hooks/useEchelleDesSprites";
import { ECHELLE_LARGE } from "../../lib/bureau/echelleDesSprites";
import { useEtirementDuSol, useMarcheActive } from "../../hooks/useEtirementDuSol";

interface AgentsDeLaPieceProps {
  projet: string;
  agents: readonly AgentPlace[];
  /** Le rôle montré à chaque poste ; à défaut, le rôle du poste (l'architecte tient celui du codeur). */
  roles?: Partial<Record<PosteId, RoleAffiche>>;
  /** Les rédacteurs de la documentation, debout devant la bibliothèque tant qu'elle tourne (ticket-624). */
  redacteurs?: readonly RedacteurPlace[];
  /** Le poste derrière lequel se tient le directeur en visite dans cette pièce (ticket-661). */
  directeur?: PosteId | null;
  /** Pourquoi il est venu, pour son infobulle (ticket-723). */
  motifDuDirecteur?: MotifDeVisite;
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

interface AgentMarcheurProps {
  projet: string;
  /** Ce que porte `data-agent` : le poste, ou le rôle d'un agent sans poste. */
  id: string;
  agent: Placement;
  role: RoleAffiche;
  bavarde: boolean;
}

function AgentMarcheur({ projet, id, agent, role, bavarde }: AgentMarcheurProps) {
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
    : (() => {
        const libelle = avecLeNom(projet, role, `${nomDuPoste(role)}, ${libelleActivite(agent.activite ?? "tasse")}`);
        // Le même texte au survol qu'à son poste : la couche ignore le pointeur, l'agent le reprend.
        return { role: "img", "aria-label": libelle, title: libelle };
      })();
  return (
    <span
      data-agent={id}
      data-activite={agent.activite ?? "parti"}
      data-objet={rendSaCopie ? "feuille" : undefined}
      className={`${marche ? "marche " : ""}${agent.parti ? "" : "pointer-events-auto "}absolute left-0 z-10`}
      style={style}
      {...acces}
    >
      {bavarde && <Bavardage />}
      <Agrandi>
        <AgentDebout
          projet={projet}
          role={role}
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
export default function AgentsDeLaPiece({ projet, agents, roles = {}, redacteurs = [], directeur = null, motifDuDirecteur }: AgentsDeLaPieceProps) {
  const bavard = quiBavarde(agents);
  return (
    <div className="pointer-events-none absolute inset-0">
      {agents.map((agent) => (
        <AgentMarcheur
          key={agent.poste}
          projet={projet}
          id={agent.poste}
          agent={agent}
          role={roles[agent.poste] ?? agent.poste}
          bavarde={agent.poste === bavard}
        />
      ))}
      {redacteurs.map((redacteur) => (
        <AgentMarcheur
          key={redacteur.role}
          projet={projet}
          id={redacteur.role}
          agent={redacteur}
          role={redacteur.role}
          bavarde={false}
        />
      ))}
      {directeur !== null && <DirecteurEnVisite projet={projet} poste={directeur} motif={motifDuDirecteur} />}
    </div>
  );
}
