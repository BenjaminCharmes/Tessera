/** « Kadoomi — listes d'envies » → le nom, puis ce qu'il fait ; sans tiret, le nom seul (ticket-735). */
export function titreEtSousTitre(nom: string): { titre: string; sousTitre: string | null } {
  const i = nom.indexOf(" — ");
  return i < 0 ? { titre: nom, sousTitre: null } : { titre: nom.slice(0, i), sousTitre: nom.slice(i + 3) };
}
