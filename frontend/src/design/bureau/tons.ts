import type { EtatPastille } from "../ui/StatusPill";
import type { SanteAgent } from "../../lib/santeAgent";
import type { EtatDuService } from "../etatDuService";

/** Ce qu'un poste montre : la santé du run s'il est occupé, sinon « fait » ou « libre ». */
export type TonDePoste = SanteAgent | "fait" | "libre";

/** Fond et texte de la bulle : les mêmes teintes que la pastille d'état. */
export const TON_BULLE: Record<SanteAgent, string> = {
  actif: "bg-blue-500/12 text-blue-300",
  attente: "bg-zinc-500/12 text-zinc-300",
  question: "bg-amber-500/12 text-amber-300",
  blocage_suspecte: "bg-red-500/12 text-red-300",
};

/** Le signe de la bulle : silencieux, question, figé ? ; `null` quand l'agent travaille. */
export const SIGNE_BULLE: Record<SanteAgent, string | null> = {
  actif: null,
  attente: "…",
  question: "?",
  blocage_suspecte: "!",
};

/** La pastille d'état qui porte le libellé de santé. */
export const ETAT_PASTILLE: Record<SanteAgent, EtatPastille> = {
  actif: "en-cours",
  attente: "neutre",
  question: "attention",
  blocage_suspecte: "echec",
};

/** La puce d'un poste dans la rangée compacte. */
export const TON_PUCE: Record<TonDePoste, string> = {
  actif: "bg-blue-400",
  attente: "bg-zinc-500",
  question: "bg-amber-400",
  blocage_suspecte: "bg-red-400",
  fait: "bg-green-400",
  libre: "bg-zinc-700",
};

/** Le même état en texte et en pastille, pour l'écran mural et la plaque de la salle (ticket-711). */
export const TEXTE_DE_L_ETAT: Record<EtatDuService, string> = {
  "en-cours": "text-blue-300",
  echoue: "text-red-300",
  arrete: "text-zinc-400",
  "jamais-lance": "text-zinc-500",
};

export const PASTILLE_DE_L_ETAT: Record<EtatDuService, string> = {
  "en-cours": "bg-blue-400",
  echoue: "bg-red-500",
  arrete: "bg-zinc-500",
  "jamais-lance": "bg-zinc-600",
};
