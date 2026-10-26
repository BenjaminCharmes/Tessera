/**
 * L'heure à laquelle une fenêtre de quota reprend, dans le fuseau de l'écran.
 * Le jour de la semaine s'ajoute quand ce n'est pas aujourd'hui : « 09:00 »
 * seul serait faux pour une fenêtre de sept jours. `null` si la date est illisible.
 */
export function heureDeReprise(iso: string, maintenant: number): string | null {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const heure = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (date.toDateString() === new Date(maintenant).toDateString()) return heure;
  return `${date.toLocaleDateString([], { weekday: "short" })} ${heure}`;
}
