import StatusPill from "../../design/ui/StatusPill";
import type { EtatPastille } from "../../design/ui/StatusPill";
import { useMaintenant } from "../../hooks/useMaintenant";
import { LIBELLE_SANTE, santeAgent } from "../../lib/santeAgent";
import type { SanteAgent } from "../../lib/santeAgent";

interface PastilleSanteProps {
  dernierEvenementA: string | null | undefined;
  pendingQuestion: string | null | undefined;
  /** Une attente extérieure est en cours : le silence est voulu (ticket-564). */
  attenteExterieure?: boolean;
}

const ETATS: Record<SanteAgent, EtatPastille> = {
  actif: "en-cours",
  attente: "neutre",
  question: "attention",
  blocage_suspecte: "echec",
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
export default function PastilleSante({
  dernierEvenementA,
  pendingQuestion,
  attenteExterieure = false,
}: PastilleSanteProps) {
  const maintenant = useMaintenant();
  const sante = santeAgent(dernierEvenementA, maintenant, pendingQuestion, attenteExterieure);

  return (
    <StatusPill
      etat={ETATS[sante]}
      libelle={LIBELLE_SANTE[sante]}
      titre={depuis(dernierEvenementA, maintenant)}
    />
  );
}
