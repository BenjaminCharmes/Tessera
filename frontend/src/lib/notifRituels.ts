import type { Rituel } from "./apiRituels";
import type { Notif } from "./notifications";

/**
 * La cloche d'un rituel en retard — ticket-904.
 *
 * Une notification par échéance : la clé `id + derniere` se garde dans
 * `localStorage`, pour qu'un rechargement ne renotifie pas. La pastille de
 * l'onglet reste la trace durable.
 */
const CLE = "notifications.rituels";

function lireCles(): Set<string> {
  try {
    const brut: unknown = JSON.parse(window.localStorage.getItem(CLE) ?? "[]");
    return new Set(Array.isArray(brut) ? brut.filter((c): c is string => typeof c === "string") : []);
  } catch {
    return new Set();
  }
}

function ecrireCles(cles: Set<string>): void {
  try {
    window.localStorage.setItem(CLE, JSON.stringify([...cles]));
  } catch {
    // Stockage indisponible : au pire, une notification de plus après rechargement.
  }
}

const cle = (r: Rituel): string => `${r.id}|${r.derniere ?? ""}`;

function heureDe(derniere: string | null): string {
  return derniere && derniere.length >= 16 ? derniere.slice(11, 16) : "l'échéance";
}

/** Rend une notification pour chaque rituel passé en retard dont l'échéance n'a pas encore sonné. */
export function notificationsRituels(avant: Rituel[], apres: Rituel[]): Notif[] {
  const connues = new Set(avant.filter((r) => r.statut === "en_retard").map(cle));
  const notifiees = lireCles();
  const notifs: Notif[] = [];
  for (const r of apres) {
    const k = cle(r);
    if (r.statut !== "en_retard" || notifiees.has(k)) continue;
    notifiees.add(k);
    // Déjà en retard à la lecture précédente : elle a pu la dire.
    if (connues.has(k)) continue;
    notifs.push({
      projectId: r.projets[0] ?? "",
      type: "rituel",
      titre: r.titre,
      corps: `En retard depuis ${heureDe(r.derniere)}. Dire à Claude : « ${r.phrase} ».`,
    });
  }
  if (notifs.length > 0) ecrireCles(notifiees);
  return notifs;
}
