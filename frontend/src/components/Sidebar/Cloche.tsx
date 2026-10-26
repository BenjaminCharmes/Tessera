import { useCallback, useState } from "react";
import { IconBell } from "../../design/icons";
import type { DonneesDeLaCloche } from "../../hooks/useNotificationsSysteme";
import { PanneauAujourdhui, PanneauReglagesDesTypes } from "./ContenuDeLaCloche";
import { useFermetureAuDehors } from "./useFermetureAuDehors";

/**
 * La cloche au pied du rail — ticket-554.
 *
 * Elle garde ce qui s'est passé aujourd'hui, envoyé au système ou non, et
 * règle événement par événement ce qui sort de l'appli. La pastille compte les
 * non-lus : violette, en fond — le violet est l'identité, jamais un état ni la
 * couleur d'un mot (ADR-026).
 */
type Onglet = "aujourdhui" | "reglages";

const ONGLETS: { id: Onglet; label: string }[] = [
  { id: "aujourdhui", label: "Aujourd'hui" },
  { id: "reglages", label: "Réglages" },
];

export default function Cloche({ cloche }: { cloche: DonneesDeLaCloche }) {
  const [ouvert, setOuvert] = useState(false);
  const [onglet, setOnglet] = useState<Onglet>("aujourdhui");
  const fermer = useCallback(() => setOuvert(false), []);
  const conteneur = useFermetureAuDehors(ouvert, fermer);
  const { nonLus } = cloche;
  const libelle =
    nonLus === 0 ? "Notifications" : `Notifications, ${nonLus} non lue${nonLus > 1 ? "s" : ""}`;

  return (
    <div ref={conteneur} className="relative px-1.5 pb-1">
      <button
        type="button"
        aria-label={libelle}
        aria-haspopup="dialog"
        aria-expanded={ouvert}
        onClick={() => setOuvert((v) => !v)}
        className={`relative flex w-full items-center justify-center rounded-md px-1 py-2 transition-colors ${
          ouvert
            ? "bg-violet-500/15 text-zinc-100 ring-1 ring-inset ring-violet-500/40"
            : "text-zinc-500 hover:bg-zinc-800/60 hover:text-zinc-200"
        }`}
      >
        <IconBell size={20} />
        {nonLus > 0 ? (
          <span
            aria-hidden="true"
            className="absolute right-0.5 top-0.5 min-w-4 rounded-full bg-violet-500 px-1 text-micro font-medium leading-4 text-zinc-50"
          >
            {nonLus}
          </span>
        ) : null}
      </button>

      {ouvert ? (
        <div
          role="dialog"
          aria-label="Notifications"
          className="absolute bottom-0 left-full z-30 ml-1 w-80 rounded-md border border-zinc-700 bg-zinc-900 shadow-lg"
        >
          <div role="tablist" aria-label="Cloche" className="flex border-b border-zinc-800">
            {ONGLETS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={onglet === id}
                onClick={() => setOnglet(id)}
                className={`flex-1 px-3 py-2 text-micro ${
                  onglet === id
                    ? "bg-violet-500/15 text-zinc-100"
                    : "text-zinc-500 hover:text-zinc-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          {onglet === "aujourdhui" ? (
            <PanneauAujourdhui
              historique={cloche.historique}
              nonLus={nonLus}
              onTout={cloche.toutMarquerLu}
              onOuvrir={(id) => {
                cloche.ouvrir(id);
                fermer();
              }}
            />
          ) : (
            <PanneauReglagesDesTypes reglages={cloche.reglages} setReglage={cloche.setReglage} />
          )}
        </div>
      ) : null}
    </div>
  );
}
