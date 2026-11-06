import { useEffect, useState } from "react";
import Button from "../../design/ui/Button";
import { lireLeRecap } from "../../lib/apiSupervision";
import { jourDe, lireDerniereVisite, memoriserVisite } from "../../lib/bureau/derniereVisite";
import type { RecapSupervision } from "../../types/supervision";

interface RecapSuperviseurProps {
  onFermer: () => void;
}

type Lecture =
  | { etat: "chargement" }
  | { etat: "erreur" }
  | { etat: "pret"; recap: RecapSupervision };

const LONGUEUR_DU_SHA = 7;

/**
 * Le journal du superviseur depuis la dernière visite, en lecture seule (ADR-080) :
 * ni bouton pour accepter, ni bouton pour défaire. La date de visite vit en
 * `localStorage` ; elle n'avance qu'à la fermeture, pour qu'une relecture
 * pendant la session montre la même chose.
 */
export default function RecapSuperviseur({ onFermer }: RecapSuperviseurProps) {
  const [depuis] = useState(lireDerniereVisite);
  const [lecture, setLecture] = useState<Lecture>({ etat: "chargement" });

  useEffect(() => {
    let abandonne = false;
    const poser = (suite: Lecture) => {
      if (!abandonne) setLecture(suite);
    };
    lireLeRecap(depuis).then(
      (recap) => poser({ etat: "pret", recap }),
      () => poser({ etat: "erreur" }),
    );
    return () => {
      abandonne = true;
    };
  }, [depuis]);

  function fermer() {
    memoriserVisite(jourDe(new Date()));
    onFermer();
  }

  return (
    <section
      aria-label="Récap du superviseur"
      className="flex flex-col gap-1.5 rounded-md border border-zinc-800 bg-zinc-950 p-2"
    >
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-xs font-semibold text-zinc-200">Récap du superviseur</h4>
        <Button taille="compact" onClick={fermer}>
          Fermer
        </Button>
      </div>
      <p className="text-micro text-zinc-500">
        {depuis === null ? "Depuis le début" : `Depuis le ${depuis}`}
      </p>
      <Corps lecture={lecture} />
    </section>
  );
}

function Corps({ lecture }: { lecture: Lecture }) {
  if (lecture.etat === "chargement") {
    return <p className="text-micro text-zinc-500">Lecture du journal…</p>;
  }
  if (lecture.etat === "erreur") {
    return <p className="text-micro text-amber-600">Le journal n'a pas pu être lu.</p>;
  }
  const { lignes } = lecture.recap;
  if (lignes.length === 0) {
    return <p className="text-micro text-zinc-500">Rien à signaler : le superviseur n'a rien fait depuis.</p>;
  }
  return (
    <ul className="flex flex-col gap-1">
      {lignes.map((ligne, i) => (
        <li key={`${ligne.sha}-${i}`} className="flex flex-col text-xs text-zinc-300">
          <span>
            <span className="text-micro text-zinc-500">{ligne.jour}</span> {ligne.action} · {ligne.cible}
          </span>
          <span className="text-micro text-zinc-500">
            {ligne.sha.slice(0, LONGUEUR_DU_SHA)}
            {ligne.resume ? ` · ${ligne.resume}` : ""}
          </span>
        </li>
      ))}
    </ul>
  );
}
