import { useCallback, useState } from "react";
import { IconEngrenage } from "../../design/icons";
import PanneauReglages from "./PanneauReglages";
import { useFermetureAuDehors } from "./useFermetureAuDehors";

/**
 * Le bouton « Réglages » au pied du rail, sous la cloche (ADR-075, ticket-810) :
 * le même ressort que `Cloche`, un popover et non une destination.
 */
export default function BoutonReglages() {
  const [ouvert, setOuvert] = useState(false);
  const fermer = useCallback(() => setOuvert(false), []);
  const conteneur = useFermetureAuDehors(ouvert, fermer);

  return (
    <div ref={conteneur} className="relative px-1.5 pb-1.5">
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
        <IconEngrenage size={20} />
      </button>
      {ouvert ? (
        <div
          role="dialog"
          aria-label="Réglages globaux"
          className="absolute bottom-0 left-full z-30 ml-1 max-h-[80vh] w-96 overflow-y-auto rounded-md border border-zinc-700 bg-zinc-900 shadow-lg"
        >
          <PanneauReglages />
        </div>
      ) : null}
    </div>
  );
}
