import { api } from "../../lib/api";
import type { QuotaWindows } from "../../lib/quota";
import type { StatutDuRun } from "../../lib/statutDuRun";
import type { VentilationDuProjet } from "../../lib/ventilation";
import type { PlanDeNettoyage } from "../../types/api";
import { resoudre, schemaDeLaReponse, type Schema } from "./openapi";
import { type Verbe } from "./registre";

/** Ce que la promesse d'une fonction du client rend : le type que le front croit lire. */
type Retour<F extends (...args: never[]) => Promise<unknown>> = Awaited<ReturnType<F>>;

/**
 * Les clés d'un type, écrites une fois. `Record<keyof T, true>` fait que `tsc`
 * refuse une clé en trop et une clé oubliée : la liste dit donc exactement ce
 * que l'interface déclare, et le test la lit à l'exécution.
 */
function champs<T extends object>(cles: Record<keyof T, true>): string[] {
  return Object.keys(cles).sort();
}

/** Un type du front face au schéma qu'il prétend lire. */
export interface Confrontation {
  libelle: string;
  verbe: Verbe;
  route: string;
  /** Le chemin jusqu'à l'objet dans la réponse : `[]` pour les éléments d'un tableau, un nom pour une propriété. */
  descente: string[];
  declares: string[];
  /** Champs du schéma que le front ne déclare pas exprès, avec la raison. */
  ecartes?: Record<string, string>;
}

const PROJET = "/api/v1/projects/{project_id}";
type Service = Retour<typeof api.services.list>[number];
type Demarres = Retour<typeof api.services.start>;
type Arretes = Retour<typeof api.services.stop>;
type Arrete = StatutDuRun["arretes"][number];
type Fenetre = NonNullable<QuotaWindows["windows"][string]>;

export const CONFRONTATIONS: Confrontation[] = [
  {
    libelle: "StatutDuRun",
    verbe: "get",
    route: "/api/v1/runs/{run_id}",
    descente: [],
    declares: champs<StatutDuRun>({
      project_id: true, mode: true, statut: true, ticket_courant: true, approuves: true,
      restants: true, debut: true, fin: true, arretes: true,
    }),
    ecartes: { faits: "déprécié, calculé : approuves suivis des tickets de arretes" },
  },
  {
    libelle: "StatutDuRun.arretes[]",
    verbe: "get",
    route: "/api/v1/runs/{run_id}",
    descente: ["arretes", "[]"],
    declares: champs<Arrete>({ ticket_id: true, motif: true }),
  },
  {
    libelle: "VentilationDuProjet",
    verbe: "get",
    route: `${PROJET}/usage/breakdown`,
    descente: [],
    declares: champs<VentilationDuProjet>({
      project_id: true, total_cost_usd: true, per_agent: true, per_model: true, per_project: true,
    }),
  },
  {
    libelle: "VentilationDuProjet.per_agent[]",
    verbe: "get",
    route: `${PROJET}/usage/breakdown`,
    descente: ["per_agent", "[]"],
    declares: champs<VentilationDuProjet["per_agent"][number]>({
      role: true, total_cost_usd: true, total_tokens: true, call_count: true,
    }),
  },
  {
    libelle: "QuotaWindows",
    verbe: "get",
    route: "/api/v1/usage/quota",
    descente: [],
    declares: champs<QuotaWindows>({ windows: true }),
  },
  {
    libelle: "QuotaWindows.windows{}",
    verbe: "get",
    route: "/api/v1/usage/quota",
    descente: ["windows", "{}"],
    declares: champs<Fenetre>({ status: true, utilization: true, resets_at: true, observed_at: true }),
  },
  {
    libelle: "ServiceActif (liste)",
    verbe: "get",
    route: `${PROJET}/services`,
    descente: ["[]"],
    declares: champs<Service>({
      nom: true, project_id: true, pid: true, demarre_a: true, en_cours: true,
      code_de_sortie: true, sortie: true, arrete_a_la_main: true,
    }),
  },
  {
    libelle: "services/start",
    verbe: "post",
    route: `${PROJET}/services/start`,
    descente: [],
    declares: champs<Demarres>({ services: true }),
  },
  {
    libelle: "services/stop",
    verbe: "post",
    route: `${PROJET}/services/stop`,
    descente: [],
    declares: champs<Arretes>({ arretes: true }),
  },
  {
    libelle: "PlanDeNettoyage",
    verbe: "get",
    route: `${PROJET}/branches/cleanup`,
    descente: [],
    declares: champs<PlanDeNettoyage>({ nettoyables: true, conservees: true }),
  },
];

/** Suit `descente` dans `schema` : `[]` entre dans les éléments, `{}` dans les valeurs d'une table. */
export function descendre(schema: Schema, descente: string[]): Schema {
  return descente.reduce<Schema>((courant, pas) => {
    const resolu = resoudre(courant);
    if (pas === "[]" && resolu.items) return resolu.items;
    if (pas === "{}" && typeof resolu.additionalProperties === "object") return resolu.additionalProperties;
    const enfant = resolu.properties?.[pas];
    if (enfant === undefined) throw new Error(`Pas « ${pas} » introuvable dans le schéma`);
    return enfant;
  }, schema);
}

/** Le schéma que vise une confrontation. */
export function schemaVise(c: Confrontation): Schema {
  return descendre(schemaDeLaReponse(c.verbe, c.route), c.descente);
}
