import type { Project } from "../../types/api";

/**
 * L'infobulle du nom de projet — ticket-441.
 *
 * Le projet qui fait tourner l'IDE y dit ce qu'il est : c'était une phrase
 * affichée en permanence sous l'en-tête, pour un état qui ne change jamais.
 */
export function titreDuProjet(project: Project): string {
  const base = `${project.id} — ${project.path ?? ""}`;
  if (!project.fait_tourner_l_ide) return base;
  return `${base}\nCe projet fait tourner l'IDE que tu utilises en ce moment : il n'y a rien à lancer, ses serveurs sont déjà là, démarrés hors de l'IDE.`;
}
