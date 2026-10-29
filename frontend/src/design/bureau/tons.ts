import type { EtatPastille } from "../ui/StatusPill";
import type { SanteAgent } from "../../lib/santeAgent";
import type { EtatBoite } from "../../lib/bureau/boiteAuxLettres";
import type { EtatCase } from "../../lib/bureau/criteres";
import type { EtatDuService } from "../etatDuService";
import type { RoleAffiche } from "../../lib/bureau/postesDuRun";
import type { Cheveux, Peau } from "../../lib/bureau/physique";

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

/** Une ligne du tableau blanc : grise tant que rien n'est jugé, verte si le critère passe, rouge sinon. */
export const TON_CASE: Record<EtatCase, string> = {
  attente: "fill-(--sprite-tableau-case)",
  passe: "fill-green-500",
  echoue: "fill-red-500",
};

/** Le voyant d'un étage de la baie, par état du service. Mêmes familles que le panneau des services. */
export const TON_VOYANT: Record<EtatDuService, string> = {
  "en-cours": "fill-blue-400",
  echoue: "fill-red-400",
  arrete: "fill-zinc-500",
  "jamais-lance": "fill-zinc-600",
};

/*
 * Les tons d'un personnage (ticket-595). Classes écrites en toutes lettres :
 * Tailwind ne voit pas une classe construite, et ne génèrerait pas la règle.
 */
export const FILL_PEAU: Record<Peau, string> = {
  1: "fill-(--sprite-peau-1)",
  2: "fill-(--sprite-peau-2)",
  3: "fill-(--sprite-peau-3)",
  4: "fill-(--sprite-peau-4)",
  5: "fill-(--sprite-peau-5)",
};

export const FILL_CHEVEUX: Record<Cheveux, string> = {
  1: "fill-(--sprite-cheveux-1)",
  2: "fill-(--sprite-cheveux-2)",
  3: "fill-(--sprite-cheveux-3)",
  4: "fill-(--sprite-cheveux-4)",
  5: "fill-(--sprite-cheveux-5)",
  6: "fill-(--sprite-cheveux-6)",
};

export const FILL_HAUT: Record<RoleAffiche, string> = {
  codeur: "fill-(--sprite-haut-codeur)",
  architect: "fill-(--sprite-haut-architect)",
  testeur: "fill-(--sprite-haut-testeur)",
  securite: "fill-(--sprite-haut-securite)",
  reviewer: "fill-(--sprite-haut-reviewer)",
  validateur: "fill-(--sprite-haut-validateur)",
  resolveur: "fill-(--sprite-haut-resolveur)",
  "doc-technique": "fill-(--sprite-haut-doc-technique)",
  "doc-fonctionnelle": "fill-(--sprite-haut-doc-fonctionnelle)",
};

/** L'ombre du haut : les bras, la jupe, le col de la capuche. */
export const FILL_OMBRE: Record<RoleAffiche, string> = {
  codeur: "fill-(--sprite-haut-codeur-ombre)",
  architect: "fill-(--sprite-haut-architect-ombre)",
  testeur: "fill-(--sprite-haut-testeur-ombre)",
  securite: "fill-(--sprite-haut-securite-ombre)",
  reviewer: "fill-(--sprite-haut-reviewer-ombre)",
  validateur: "fill-(--sprite-haut-validateur-ombre)",
  resolveur: "fill-(--sprite-haut-resolveur-ombre)",
  "doc-technique": "fill-(--sprite-haut-doc-technique-ombre)",
  "doc-fonctionnelle": "fill-(--sprite-haut-doc-fonctionnelle-ombre)",
};
