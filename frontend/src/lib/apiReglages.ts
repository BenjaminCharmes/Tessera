import { request } from "./http";

/** Un réglage global tel que le rend `GET /reglages` (ADR-075). */
export interface Reglage {
  nom: string;
  libelle: string;
  type: "float" | "int" | "bool";
  valeur: number | boolean;
  defaut: number | boolean;
  minimum: number | null;
  maximum: number | null;
  modifie: boolean;
  effet: "prochain_run" | "machine";
  /** Combien de runs ouverts gardent encore l'ancienne valeur. */
  runs_ouverts: number;
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export const reglages = {
  list: (): Promise<Reglage[]> => request("/reglages"),
  /** Pose une valeur ; 403 sans origine déclarée, 404 nom inconnu, 422 hors bornes. */
  ecrire: (nom: string, valeur: number | boolean): Promise<Reglage> =>
    request(`/reglages/${encodeURIComponent(nom)}`, {
      method: "PUT",
      headers: JSON_HEADERS,
      body: JSON.stringify({ valeur }),
    }),
  /** Rend le réglage à son défaut de `.env`. */
  retirer: (nom: string): Promise<Reglage> =>
    request(`/reglages/${encodeURIComponent(nom)}`, { method: "DELETE" }),
};

/** Le détail d'un 422 : le corps JSON `{"detail": "..."}` de l'API, sinon le texte brut. */
function detailDe(corps: string): string {
  try {
    const lu = JSON.parse(corps) as { detail?: unknown };
    return typeof lu.detail === "string" ? lu.detail : corps;
  } catch {
    return corps;
  }
}

/** Rend en texte lisible l'erreur d'une écriture : 403, 404 et 422 ont chacun leur phrase. */
export function texteDeLErreur(erreur: unknown): string {
  const message = erreur instanceof Error ? erreur.message : String(erreur);
  const trouve = /^API (\d{3}): ([\s\S]*)$/.exec(message);
  if (!trouve) return message;
  const [, code, corps] = trouve;
  if (code === "403") {
    return "Refusé : l'interface doit être servie depuis une origine déclarée (ALLOWED_ORIGINS).";
  }
  if (code === "404") return "Ce réglage n'existe pas.";
  if (code === "422") return `Valeur refusée : ${detailDe(corps)}`;
  if (code === "401") return "Refusé : jeton d'accès manquant ou invalide.";
  return message;
}
