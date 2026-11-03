import type { RoleAffiche } from "../../lib/bureau/postesDuRun";
import { TENUES, physique } from "../../lib/bureau/physique";
import type { Physique, Tenue } from "../../lib/bureau/physique";
import { type Mains, type OptionsDebout, debout, marche } from "../../lib/bureau/sprites/debout";
import { memoise } from "../../lib/bureau/sprites/symboles";
import SpriteSvg from "./SpriteSvg";

/** La tenue et le physique d'une figure sans rôle de pipeline : le directeur. */
export interface FigureDeSalle {
  tenue: Tenue;
  physique: Physique;
}

interface AgentDeboutProps {
  projet: string;
  role: RoleAffiche;
  /** Les bras levés : il fête la PR mergée. */
  brasLeves?: boolean;
  /** Les bras le long du corps, mains vides : il fait une pause. Sinon, tasse à la main. */
  sansTasse?: boolean;
  /** Une feuille annotée à la main : il rend sa copie au codeur. */
  feuille?: boolean;
  /** Une figure de salle commune, à la place de la tenue du rôle (le directeur en visite). */
  figure?: FigureDeSalle;
  /** Il se déplace : les quatre images de la marche, tant que dure la translation. */
  enMarche?: boolean;
}

/** Un dessin par combinaison : la clé porte tout ce qui le change, rien d'autre. */
const dessiner = memoise((enMarche: boolean, cle: string) => {
  const o = JSON.parse(cle) as OptionsDebout;
  return enMarche ? marche(o) : debout(o);
});

function mainsDe(brasLeves: boolean, sansTasse: boolean, feuille: boolean): Mains {
  if (feuille) return "feuille";
  if (brasLeves) return "levees";
  return sansTasse ? "vides" : "tasse";
}

/**
 * L'agent debout, grille 24 × 40 en 42 × 70 px (ticket-727), à l'échelle du poste.
 * Un agent qui a fini sourit ; une figure de salle garde un visage neutre. Quand il se
 * déplace, il marche au lieu de glisser. `overflow-visible` : les bras levés dépassent.
 */
export default function AgentDebout({
  projet,
  role,
  brasLeves = false,
  sansTasse = false,
  feuille = false,
  figure,
  enMarche = false,
}: AgentDeboutProps) {
  const mains = mainsDe(brasLeves, sansTasse, feuille);
  const tenue = figure?.tenue ?? TENUES[role];
  const ph = figure?.physique ?? physique(projet, role);
  const expression = figure ? "neutre" : "fait";
  // Les bras levés ne marchent pas : la fête se passe sur place.
  const marcheVraiment = enMarche && mains !== "levees";
  const dessin = dessiner(marcheVraiment, JSON.stringify({ physique: ph, tenue, expression, mains }));
  return (
    <SpriteSvg
      sprite={dessin}
      largeur={42}
      hauteur={70}
      data-sprite="agent-debout"
      data-mains={mains}
      data-marche={marcheVraiment}
      data-cravate={tenue.cravate}
      data-capuche={tenue.capuche}
    />
  );
}
