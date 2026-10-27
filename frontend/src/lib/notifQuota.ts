import { heureDeReprise } from "./bureau/heureDeReprise";
import type { Notif } from "./notifications";
import type { QuotaWindowReading } from "./quota";

/** Les relevés par fenêtre, comme `GET /usage/quota` les rend (ticket-558). */
export type RelevesDeQuota = Record<string, QuotaWindowReading | undefined>;

/** Seul reste de quota sous lequel on prévient : 10 % de la fenêtre. */
const SEUIL_CONSOMME = 0.9;

// Les deux fenêtres dont la fin arrête un run : la session de cinq heures et la semaine.
const FENETRES: { cle: string; libelle: string }[] = [
  { cle: "five_hour", libelle: "la session" },
  { cle: "seven_day", libelle: "la semaine" },
];

// Comparaison sur la consommation, pas sur `1 - utilisation` : 1 - 0.9 vaut
// 0.0999… en flottant, et 10 % restants pile ne sont pas « sous » 10 %.
function estBas(releve: QuotaWindowReading | undefined): releve is QuotaWindowReading {
  return releve !== undefined && releve.utilization > SEUIL_CONSOMME;
}

/**
 * Une fenêtre qui passe sous 10 % prévient une fois, puis se tait jusqu'à ce que
 * sa période de reprise change. « Même période » : déjà basse au relevé d'avant,
 * avec la même heure de reprise.
 */
function nouvellePeriodeBasse(avant: QuotaWindowReading | undefined, apres: QuotaWindowReading): boolean {
  return !estBas(avant) || avant.resets_at !== apres.resets_at;
}

function texteDe(libelle: string, releve: QuotaWindowReading, maintenant: number): Notif {
  const restant = Math.max(0, Math.round((1 - releve.utilization) * 100));
  const reprise = releve.resets_at ? heureDeReprise(releve.resets_at, maintenant) : null;
  return {
    // Le quota est celui du compte, pas d'un projet : aucun projet à ouvrir au clic.
    projectId: "",
    type: "quota_bas",
    titre: `Quota de ${libelle} bas`,
    corps: reprise
      ? `Il reste ${restant} % du quota de ${libelle}. Reprise à ${reprise}.`
      : `Il reste ${restant} % du quota de ${libelle}. L'heure de reprise n'est pas connue.`,
  };
}

/**
 * Les notifications de quota entre deux instantanés. `undefined` des deux côtés
 * veut dire « pas encore lu » : un passage qu'on n'a pas vu ne se notifie pas,
 * sinon chaque rechargement de l'IDE préviendrait de nouveau d'un quota déjà bas.
 */
export function notificationsQuota(
  avant: RelevesDeQuota | undefined,
  apres: RelevesDeQuota | undefined,
  maintenant: number,
): Notif[] {
  if (!avant || !apres) return [];
  const notifs: Notif[] = [];
  for (const { cle, libelle } of FENETRES) {
    const releve = apres[cle];
    if (estBas(releve) && nouvellePeriodeBasse(avant[cle], releve)) {
      notifs.push(texteDe(libelle, releve, maintenant));
    }
  }
  return notifs;
}
