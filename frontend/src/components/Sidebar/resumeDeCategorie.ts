import type { Project } from "../../types/api";

/** « 3 projets : a, b, c » — dit en toutes lettres ce que le badge résume. */
export function resumeDeCategorie(projets: Project[]): string {
  const mot = projets.length > 1 ? "projets" : "projet";
  return `${projets.length} ${mot} : ${projets.map((p) => p.name).join(", ")}`;
}
