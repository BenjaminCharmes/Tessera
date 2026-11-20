import { request, send } from "./http";

export type StatutRituel = "fait" | "a_venir" | "en_retard";

export type RythmeRituel =
  | { type: "hebdo"; jour: string; heure: string }
  | { type: "mensuel"; jour: number; heure: string; avant: number | null }
  | { type: "unique"; du: string; au: string };

/** Un rituel de `rituels.md` avec son état local, tel que `GET /rituels` le rend. */
export interface Rituel {
  id: string;
  titre: string;
  rythme: RythmeRituel;
  duree_min: number;
  phrase: string;
  detail: string;
  projets: string[];
  statut: StatutRituel;
  derniere: string | null;
  prochaine: string | null;
  depasse: boolean;
  fait_le: string | null;
  reporte_jusqua: string | null;
}

export interface ListeRituels {
  rituels: Rituel[];
  erreur: string | null;
  /** `locale` : l'état n'est gardé que sur ce PC, la synchro GitHub est inactive. */
  synchro: "github" | "locale";
}

export function lireRituels(): Promise<ListeRituels> {
  return request<ListeRituels>("/rituels");
}

/** Marque un rituel fait maintenant. */
export async function marquerFait(id: string): Promise<void> {
  await send(`/rituels/${encodeURIComponent(id)}/fait`, { method: "POST" });
}

/** Reporte un rituel de 24 heures. */
export async function reporterRituel(id: string): Promise<void> {
  await send(`/rituels/${encodeURIComponent(id)}/reporter`, { method: "POST" });
}
