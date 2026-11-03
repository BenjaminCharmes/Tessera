import type { EtatPastille } from "../../design/ui/StatusPill";
import type { EtapeMiseEnLigne, EtatEtape } from "../../types/api";

/**
 * Les sept états d'une étape et leur pastille — ticket-472, maquette
 * « Mettre en ligne — déroulé des étapes ». Les familles de couleur sont celles
 * d'ADR-026 : `zinc` à faire, `green` fait, `blue` en cours, `amber` pour ce
 * qui attend l'utilisateur, `red` pour l'échec.
 */
export const ETATS: Record<EtatEtape, { libelle: string; pastille: EtatPastille }> = {
  todo: { libelle: "à faire", pastille: "neutre" },
  done: { libelle: "fait", pastille: "reussi" },
  skipped: { libelle: "déjà là", pastille: "reussi" },
  pending: { libelle: "en cours", pastille: "en-cours" },
  manual: { libelle: "à faire à la main", pastille: "attention" },
  needs_human: { libelle: "ton action requise", pastille: "attention" },
  failed: { libelle: "échec", pastille: "echec" },
};

/** Les noms d'étape du backend, lisibles ; un nom inconnu s'affiche tel quel. */
const NOMS: Record<string, string> = {
  vercel_project: "Projet Vercel",
  database: "Base Neon",
  variables: "Variables",
  resend_domain: "Domaine Resend",
  stripe: "Stripe",
  dns: "DNS",
  resend_verify: "Vérification Resend",
  redeploy: "Redéploiement",
  health_check: "Contrôle du site",
  provisioning: "Mise en ligne",
};

export function nomDEtape(step: string): string {
  return NOMS[step] ?? step;
}

function estEtat(valeur: string): valeur is EtatEtape {
  return valeur in ETATS;
}

/** Un événement `provisioning_step` de ce projet et bien formé, ou `null`. */
export function lireEvenement(
  message: Record<string, unknown>,
  projectId: string,
): EtapeMiseEnLigne | null {
  if (message.type !== "provisioning_step" || message.project_id !== projectId) return null;
  const data = message.data;
  if (typeof data !== "object" || data === null) return null;
  const { step, state, detail } = data as Record<string, unknown>;
  if (typeof step !== "string" || typeof state !== "string" || !estEtat(state)) return null;
  return { step, state, detail: typeof detail === "string" ? detail : "" };
}

/**
 * Les étapes à afficher : l'ordre vient du plan lancé, l'état lu (`GET`) puis
 * les événements recouvrent, dans cet ordre — un événement l'emporte toujours
 * sur une lecture partie avant lui. Une étape inconnue du plan (l'échec du run
 * entier) s'ajoute à la fin.
 */
export function fusionner(
  plan: string[],
  lues: EtapeMiseEnLigne[],
  evenements: EtapeMiseEnLigne[],
): EtapeMiseEnLigne[] {
  const parNom = new Map<string, EtapeMiseEnLigne>();
  for (const nom of plan) parNom.set(nom, { step: nom, state: "todo", detail: "" });
  for (const etape of [...lues, ...evenements]) parNom.set(etape.step, etape);
  return [...parNom.values()];
}

/**
 * La mise en ligne a rendu la main : un échec, une action qui attend
 * l'utilisateur, ou toutes les étapes du plan ont parlé.
 *
 * `needs_human` compte comme une fin même quand le plan continue derrière
 * (`blocks_plan` n'est pas publié) : au pire un second clic reçoit un 409.
 */
export function estTerminee(plan: string[], evenements: EtapeMiseEnLigne[]): boolean {
  if (evenements.some((e) => e.state === "failed" || e.state === "needs_human")) return true;
  const vues = new Set(evenements.map((e) => e.step));
  return plan.length > 0 && plan.every((nom) => vues.has(nom));
}
