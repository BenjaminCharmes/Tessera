/** Le libellé de la suite du pipeline (documentation, livraison), ou `null` hors de ces deux étapes. */
export function libelleDeSuite(etape: string | null): string | null {
  if (etape === "documentation") return "documentation";
  if (etape === "livraison") return "livraison : rebase, tests, PR";
  return null;
}
