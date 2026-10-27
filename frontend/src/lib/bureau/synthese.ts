/**
 * Les sons du Bureau, synthétisés — ticket-603.
 *
 * Aucun fichier audio : quelques oscillateurs courts de la Web Audio API. Un
 * navigateur sans `AudioContext`, ou qui refuse de démarrer le son avant un
 * geste, ne casse rien : le son est un confort, l'image dit déjà tout.
 */
export type Son = "fanfare" | "alarme" | "glouglou" | "frappes";

interface Note {
  /** Début de la note, en secondes après le déclenchement du son. */
  debutS: number;
  dureeS: number;
  hz: number;
  forme: OscillatorType;
  volume: number;
}

const PARTITIONS: Record<Son, readonly Note[]> = {
  // Trois notes montantes (do, mi, sol), moins d'une seconde en tout.
  fanfare: [
    { debutS: 0, dureeS: 0.18, hz: 523, forme: "triangle", volume: 0.12 },
    { debutS: 0.2, dureeS: 0.18, hz: 659, forme: "triangle", volume: 0.12 },
    { debutS: 0.4, dureeS: 0.35, hz: 784, forme: "triangle", volume: 0.12 },
  ],
  // Deux bips graves.
  alarme: [
    { debutS: 0, dureeS: 0.18, hz: 196, forme: "square", volume: 0.08 },
    { debutS: 0.3, dureeS: 0.18, hz: 196, forme: "square", volume: 0.08 },
  ],
  // Un glouglou bref : deux petites bulles qui montent.
  glouglou: [
    { debutS: 0, dureeS: 0.07, hz: 320, forme: "sine", volume: 0.1 },
    { debutS: 0.09, dureeS: 0.09, hz: 430, forme: "sine", volume: 0.1 },
  ],
  // Trois frappes de clavier très douces.
  frappes: [
    { debutS: 0, dureeS: 0.03, hz: 1800, forme: "triangle", volume: 0.03 },
    { debutS: 0.09, dureeS: 0.03, hz: 1500, forme: "triangle", volume: 0.03 },
    { debutS: 0.19, dureeS: 0.03, hz: 1700, forme: "triangle", volume: 0.03 },
  ],
};

function jouerNote(contexte: AudioContext, note: Note): OscillatorNode {
  const oscillateur = contexte.createOscillator();
  const gain = contexte.createGain();
  const debut = contexte.currentTime + note.debutS;
  oscillateur.type = note.forme;
  oscillateur.frequency.value = note.hz;
  gain.gain.setValueAtTime(note.volume, debut);
  gain.gain.exponentialRampToValueAtTime(0.001, debut + note.dureeS);
  oscillateur.connect(gain);
  gain.connect(contexte.destination);
  oscillateur.start(debut);
  oscillateur.stop(debut + note.dureeS);
  return oscillateur;
}

/** Joue un son. Ne lève jamais : sans audio, il ne se passe rien. */
export function jouerSon(son: Son): void {
  try {
    const contexte = new AudioContext();
    const oscillateurs = PARTITIONS[son].map((note) => jouerNote(contexte, note));
    const dernier = oscillateurs[oscillateurs.length - 1];
    if (dernier) dernier.onended = () => void contexte.close();
  } catch {
    // Pas de son disponible ici : on ne dit rien.
  }
}
