/**
 * Situer un coût par rapport à son plafond — ticket-197.
 *
 * ADR-026 : `zinc` est le cas nominal, `amber` l'attente ou l'alerte,
 * `red` l'échec. Jamais de violet sur un état.
 */
export type CouleurDeBudget = "zinc" | "amber" | "red";

export function couleurDuBudget(
  coutUsd: number,
  plafondUsd: number | null | undefined,
): CouleurDeBudget {
  if (!plafondUsd || plafondUsd <= 0) return "zinc";
  const part = coutUsd / plafondUsd;
  if (part >= 0.9) return "red";
  if (part >= 0.7) return "amber";
  return "zinc";
}

export const CLASSES_DE_BUDGET: Record<CouleurDeBudget, string> = {
  zinc: "bg-zinc-800 text-zinc-400",
  amber: "bg-amber-500/20 text-amber-200",
  red: "bg-red-500/20 text-red-200",
};

function usd(v: number): string {
  return `${v.toFixed(2).replace(".", ",")} $`;
}

/** « 0,84 $ · 3 appels · 47 outils », puis « sur 5,00 $ » si un plafond existe. */
export function resumeDuCout(
  coutUsd: number,
  appels: number,
  outils: number,
  plafondUsd?: number | null,
): string {
  const parts = [
    usd(coutUsd),
    `${appels} appel${appels > 1 ? "s" : ""}`,
    `${outils} outil${outils > 1 ? "s" : ""}`,
  ];
  const base = parts.join(" · ");
  return plafondUsd && plafondUsd > 0 ? `${base} sur ${usd(plafondUsd)}` : base;
}
