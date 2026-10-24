import { LIBELLE_SANTE } from "../../lib/santeAgent";
import type { SanteAgent } from "../../lib/santeAgent";
import StatusPill from "../ui/StatusPill";
import { ETAT_PASTILLE } from "./tons";

interface PastilleProps {
  sante: SanteAgent;
}

/** La pastille de santé d'une pièce : même mot que la bulle, sans minuteur. */
export default function Pastille({ sante }: PastilleProps) {
  return <StatusPill etat={ETAT_PASTILLE[sante]} libelle={LIBELLE_SANTE[sante]} />;
}
