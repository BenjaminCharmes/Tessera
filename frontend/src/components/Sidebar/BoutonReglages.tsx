import { useCallback, useState } from "react";
import { IconSettings } from "../../design/icons";
import { useFermetureAuDehors } from "./useFermetureAuDehors";
import PlafondsDeDepense from "./PlafondsDeDepense";
import ReglageNotifications, {
  type ReglageDesNotifications,
} from "./ReglageNotifications";

/**
 * Les réglages globaux, derrière un bouton au pied du rail — ticket-441.
 *
 * Notifications et plafonds de dépense valent pour tous les projets : les
 * répéter sous le nom de chaque projet laissait croire le contraire. Le panneau
 * s'ouvre à droite du rail, par-dessus la colonne, et se referme sur Échap ou
 * sur un clic en dehors.
 */
interface BoutonReglagesProps {
  notifications?: ReglageDesNotifications;
}

export default function BoutonReglages({ notifications }: BoutonReglagesProps) {
  const [ouvert, setOuvert] = useState(false);
  const fermer = useCallback(() => setOuvert(false), []);
  const conteneur = useFermetureAuDehors(ouvert, fermer);

  return (
    <div ref={conteneur} className="relative px-1.5 pb-3">
      <button
        type="button"
        aria-label="Réglages"
        aria-haspopup="dialog"
        aria-expanded={ouvert}
        onClick={() => setOuvert((v) => !v)}
        className={`flex w-full items-center justify-center rounded-md px-1 py-2 transition-colors ${
          ouvert
            ? "bg-violet-500/15 text-zinc-100 ring-1 ring-inset ring-violet-500/40"
            : "text-zinc-500 hover:bg-zinc-800/60 hover:text-zinc-200"
        }`}
      >
        <IconSettings size={20} />
      </button>

      {ouvert ? (
        <div
          role="dialog"
          aria-label="Réglages"
          className="absolute bottom-2 left-full z-30 ml-1 w-72 rounded-md border border-zinc-700 bg-zinc-900 shadow-lg"
        >
          {notifications ? (
            <ReglageNotifications
              active={notifications.active}
              etat={notifications.etat}
              onChange={notifications.onChange}
            />
          ) : null}
          <div className="px-3 py-3">
            <PlafondsDeDepense />
          </div>
        </div>
      ) : null}
    </div>
  );
}
