import StatusPill from "../../design/ui/StatusPill";
import type { EtatPastille } from "../../design/ui/StatusPill";
import { useMaintenant } from "../../hooks/useMaintenant";
import { santeAgent } from "../../lib/santeAgent";
import type { SanteAgent } from "../../lib/santeAgent";

interface PastilleSanteProps {
  dernierEvenementA: string | null | undefined;
  pendingQuestion: string | null | undefined;
}

const PASTILLES: Record<SanteAgent, { etat: EtatPastille; libelle: string }> = {
  actif: { etat: "en-cours", libelle: "travaille" },
  attente: { etat: "neutre", libelle: "silencieux" },
  question: { etat: "attention", libelle: "question" },
  blocage_suspecte: { etat: "echec", libelle: "figé ?" },
};

function depuis(dernierEvenementA: string | null | undefined, maintenant: number): string {
  const debut = dernierEvenementA ? Date.parse(dernierEvenementA) : Number.NaN;
  if (Number.isNaN(debut)) return "Aucun événement reçu pour l'instant";
  const secondes = Math.max(0, Math.round((maintenant - debut) / 1000));
  return `Dernier événement il y a ${secondes} s`;
}

/**
 * Pastille de santé de l'agent en cours. Le tick de l'horloge vit ici : seule
 * la pastille se redessine, pas toute la vue du run.
 */
export default function PastilleSante({ dernierEvenementA, pendingQuestion }: PastilleSanteProps) {
  const maintenant = useMaintenant();
  const sante = santeAgent(dernierEvenementA, maintenant, pendingQuestion);
  const { etat, libelle } = PASTILLES[sante];

  return <StatusPill etat={etat} libelle={libelle} titre={depuis(dernierEvenementA, maintenant)} />;
}
