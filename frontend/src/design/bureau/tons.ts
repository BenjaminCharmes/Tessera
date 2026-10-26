import type { EtatPastille } from "../ui/StatusPill";
import type { SanteAgent } from "../../lib/santeAgent";
import type { EtatBoite } from "../../lib/bureau/boiteAuxLettres";
import type { EtatDuService } from "../etatDuService";

/** Ce qu'un poste montre : la santé du run s'il est occupé, sinon « fait » ou « libre ». */
export type TonDePoste = SanteAgent | "fait" | "libre";

/** Le pixel allumé de l'écran. Familles d'état seulement (ADR-026). */
export const TON_ECRAN: Record<TonDePoste, string> = {
  actif: "fill-blue-400",
  attente: "fill-zinc-500",
  question: "fill-amber-400",
  blocage_suspecte: "fill-red-400",
  fait: "fill-zinc-700",
  libre: "fill-zinc-900",
};

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

/** Le drapeau de la boîte aux lettres, par état de la PR. L'absence de PR ne lève rien. */
export const TON_BOITE: Record<Exclude<EtatBoite, "aucune">, string> = {
  ouverte: "fill-amber-400",
  ci: "fill-blue-400",
  mergee: "fill-green-400",
  refusee: "fill-red-400",
};

/** Le voyant d'un étage de la baie, par état du service. Mêmes familles que le panneau des services. */
export const TON_VOYANT: Record<EtatDuService, string> = {
  "en-cours": "fill-blue-400",
  echoue: "fill-red-400",
  arrete: "fill-zinc-500",
  "jamais-lance": "fill-zinc-600",
};
