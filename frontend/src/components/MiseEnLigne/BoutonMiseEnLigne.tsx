import { useState } from "react";
import Button from "../../design/ui/Button";
import type { ProjectOverview } from "../../types/api";
import Confirmation from "./Confirmation";
import Deroule from "./Deroule";
import { useMiseEnLigne } from "./useMiseEnLigne";

type Phase = "aucune" | "confirmation" | "deroule";

/**
 * « Mettre en ligne » sur la carte d'un projet — ticket-472.
 *
 * Absent sans bloc `online` dans `agents.json`. Le clic ouvre la confirmation ;
 * rien n'est appelé avant qu'elle soit confirmée. Le bouton reste désactivé
 * tant que la mise en ligne tourne, et un refus (409, bloc invalide) l'affiche
 * en une ligne en le laissant disponible. Les clics ne remontent pas à la
 * carte, qui ouvrirait les tickets.
 */
export default function BoutonMiseEnLigne({ projet }: { projet: ProjectOverview }) {
  const [fenetre, setFenetre] = useState<Phase>("aucune");
  const { etapes, enCours, erreur, demarrer } = useMiseEnLigne(projet.id);

  if (!projet.online_declared) return null;

  const domaine = projet.online_domain ?? null;
  const modeStripe = projet.online_stripe_mode ?? null;

  async function confirmer() {
    setFenetre("aucune");
    if (await demarrer()) setFenetre("deroule");
  }

  return (
    <div className="flex min-w-0 shrink-0 flex-col items-end gap-1">
      <div className="flex gap-1.5">
        {etapes.length > 0 && (
          <Button
            variante="discret"
            taille="compact"
            onClick={(e) => {
              e.stopPropagation();
              setFenetre("deroule");
            }}
          >
            Voir les étapes
          </Button>
        )}
        <Button
          taille="compact"
          disabled={enCours}
          onClick={(e) => {
            e.stopPropagation();
            setFenetre("confirmation");
          }}
        >
          {enCours ? "Mise en ligne…" : "Mettre en ligne"}
        </Button>
      </div>
      {erreur && fenetre === "aucune" && (
        <p role="alert" className="line-clamp-2 max-w-56 text-right text-micro text-red-400">
          {erreur}
        </p>
      )}
      {fenetre === "confirmation" && (
        <Confirmation
          nom={projet.name}
          domaine={domaine}
          modeStripe={modeStripe}
          onConfirmer={() => void confirmer()}
          onAnnuler={() => setFenetre("aucune")}
        />
      )}
      {fenetre === "deroule" && (
        <Deroule
          nom={projet.name}
          domaine={domaine}
          modeStripe={modeStripe}
          etapes={etapes}
          enCours={enCours}
          erreur={erreur}
          onFermer={() => setFenetre("aucune")}
          onRelancer={() => setFenetre("confirmation")}
        />
      )}
    </div>
  );
}
