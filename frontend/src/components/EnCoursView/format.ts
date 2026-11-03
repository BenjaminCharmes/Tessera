import type { AppEnCours } from "../../types/api";

/** Mémoire en Mo, une décimale : la somme affichée reste celle des lignes. */
export function formaterMo(mo: number): string {
  return `${mo.toFixed(1).replace(".", ",")} Mo`;
}

/** L'heure de démarrage, « HH:MM » à l'heure locale, ou « — » quand elle est inconnue. */
export function formaterHeure(demarreA: string | null): string {
  if (demarreA === null) return "—";
  const debut = Date.parse(demarreA);
  if (Number.isNaN(debut)) return "—";
  return new Date(debut).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

export interface GroupeDeProjet {
  project_id: string;
  project_name: string;
  apps: AppEnCours[];
  memoire_mo: number;
}

export function memoireTotale(apps: AppEnCours[]): number {
  return apps.reduce((somme, app) => somme + app.memoire_mo, 0);
}

/**
 * Regroupe par projet. Les apps d'un groupe, et les groupes entre eux (par
 * mémoire cumulée), vont du plus gourmand au plus sobre.
 */
export function grouperParProjet(apps: AppEnCours[]): GroupeDeProjet[] {
  const groupes = new Map<string, GroupeDeProjet>();
  for (const app of apps) {
    const groupe = groupes.get(app.project_id) ?? {
      project_id: app.project_id,
      project_name: app.project_name,
      apps: [],
      memoire_mo: 0,
    };
    groupe.apps.push(app);
    groupe.memoire_mo += app.memoire_mo;
    groupes.set(app.project_id, groupe);
  }
  const liste = [...groupes.values()];
  for (const groupe of liste) {
    groupe.apps.sort((a, b) => b.memoire_mo - a.memoire_mo);
  }
  return liste.sort((a, b) => b.memoire_mo - a.memoire_mo);
}
