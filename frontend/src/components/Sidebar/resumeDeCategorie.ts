/** « 3 projets : a, b, c » — dit en toutes lettres ce que le badge résume. */
export function resumeDeCategorie(projets: ReadonlyArray<{ name: string }>): string {
  const mot = projets.length > 1 ? "projets" : "projet";
  return `${projets.length} ${mot} : ${projets.map((p) => p.name).join(", ")}`;
}
