/** L'angle de chaque aiguille, en degrés dans le sens horaire, depuis midi. */
export interface AiguillesDeLHorloge {
  heure: number;
  minute: number;
}

/**
 * Les aiguilles de l'horloge murale à l'instant `maintenant` (millisecondes), heure
 * locale comme le ciel des fenêtres. L'instant vient de l'horloge unique de la vue :
 * aucun minuteur n'est ouvert ici. L'aiguille des heures avance avec les minutes.
 */
export function aiguillesDeLHorloge(maintenant: number): AiguillesDeLHorloge {
  const d = new Date(maintenant);
  const minutes = d.getMinutes();
  return {
    heure: (d.getHours() % 12) * 30 + minutes * 0.5,
    minute: minutes * 6,
  };
}
