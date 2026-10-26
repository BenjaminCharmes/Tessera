/**
 * Un bip court pour une question qui arrive — ticket-566.
 *
 * Synthétisé : aucun fichier audio à embarquer. Un navigateur qui refuse de
 * démarrer le son avant un geste de l'utilisateur, ou qui n'a pas d'`AudioContext`,
 * ne casse rien : l'alerte sonore est un confort, la question reste affichée.
 */
const DUREE_S = 0.25;
const FREQUENCE_HZ = 880;

export function jouerBip(): void {
  try {
    const contexte = new AudioContext();
    const oscillateur = contexte.createOscillator();
    const gain = contexte.createGain();
    oscillateur.frequency.value = FREQUENCE_HZ;
    gain.gain.setValueAtTime(0.15, contexte.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, contexte.currentTime + DUREE_S);
    oscillateur.connect(gain).connect(contexte.destination);
    oscillateur.start();
    oscillateur.stop(contexte.currentTime + DUREE_S);
    oscillateur.onended = () => void contexte.close();
  } catch {
    // Pas de son disponible ici : on ne dit rien.
  }
}
