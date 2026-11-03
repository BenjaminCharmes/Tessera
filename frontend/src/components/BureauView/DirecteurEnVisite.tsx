import Agrandi from "../../design/bureau/Agrandi";
import AgentDebout from "../../design/bureau/AgentDebout";
import { useEchelleDesSprites } from "../../hooks/useEchelleDesSprites";
import { useEtirementDuSol, useMarcheActive } from "../../hooks/useEtirementDuSol";
import { DECALAGE_A_COTE, centreDuPoste } from "../../lib/bureau/activites";
import { ECHELLE_LARGE } from "../../lib/bureau/echelleDesSprites";
import { NOM_DU_DIRECTEUR } from "../../lib/bureau/noms";
import type { PosteId } from "../../lib/bureau/postesDuRun";
import type { MotifDeVisite } from "../../lib/bureau/ronde";
import { PHYSIQUE_DU_DIRECTEUR, TENUE_DU_DIRECTEUR } from "../../lib/bureau/sallesCommunes";

/** Ce que fait le directeur, selon ce qui l'a fait venir (ticket-723). */
const RAISON: Record<MotifDeVisite, string> = {
  demande: "en visite",
  silence: "vient voir pourquoi le run se tait",
  "tour-refuse": "vient voir le refus du reviewer",
  approuve: "vient féliciter le validateur",
};

/** Hauteur du pied du directeur au-dessus du bas du sol : celle des agents debout de la pièce. */
const BAS_DE_LA_RANGEE = 28;
const FIGURE = { tenue: TENUE_DU_DIRECTEUR, physique: PHYSIQUE_DU_DIRECTEUR };

interface DirecteurEnVisiteProps {
  projet: string;
  /** Le poste de l'agent derrière lequel il se tient. */
  poste: PosteId;
  motif?: MotifDeVisite;
}

/**
 * Le directeur, debout derrière l'agent de `poste` : il a quitté son bureau pour
 * cette visite (ticket-661). Posé comme un agent debout de la pièce, au même repère ;
 * la couche des agents ne reçoit aucun clic, les postes dessous restent des boutons.
 */
export default function DirecteurEnVisite({ projet, poste, motif = "demande" }: DirecteurEnVisiteProps) {
  const etirement = useEtirementDuSol();
  const marche = useMarcheActive();
  const decalage = (DECALAGE_A_COTE * useEchelleDesSprites()) / ECHELLE_LARGE;
  const libelle = `${NOM_DU_DIRECTEUR}, directeur, ${RAISON[motif]} chez ${projet}`;
  return (
    <span
      data-directeur="visite"
      data-poste={poste}
      role="img"
      aria-label={libelle}
      title={libelle}
      className={`${marche ? "marche " : ""}pointer-events-auto absolute left-0 z-10`}
      style={{
        bottom: BAS_DE_LA_RANGEE,
        transform: `translate(${centreDuPoste(poste) * etirement + decalage}px, 0px)`,
      }}
    >
      <Agrandi>
        <AgentDebout projet={projet} role={poste} figure={FIGURE} />
      </Agrandi>
    </span>
  );
}
