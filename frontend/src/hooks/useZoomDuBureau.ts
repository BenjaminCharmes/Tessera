import { useLayoutEffect, useRef, useState } from "react";
import { useEtatPersistant } from "./useEtatPersistant";
import { estModeDeZoom, zoomPourAjuster } from "../lib/bureau/zoomDuBureau";
import type { ModeDeZoom } from "../lib/bureau/zoomDuBureau";

/** Le padding vertical du conteneur qui défile (`p-3`) : il ne reçoit pas de pièce. */
const PADDING_VERTICAL = 24;

/**
 * Le zoom du Bureau et ce qu'il faut pour le mesurer — ticket-657. Le mode est
 * mémorisé ; « ajusté » se recalcule quand la vue ou son contenu change de taille.
 */
export function useZoomDuBureau() {
  const [mode, setMode] = useEtatPersistant<ModeDeZoom>(
    "bureau.zoom",
    1,
    estModeDeZoom,
  );
  const conteneur = useRef<HTMLDivElement>(null);
  const contenu = useRef<HTMLDivElement>(null);
  const [ajuste, setAjuste] = useState(1);

  useLayoutEffect(() => {
    if (mode !== "ajuste") return;
    const boite = conteneur.current;
    const pieces = contenu.current;
    if (!boite || !pieces) return;
    const mesurer = () => {
      // La hauteur rendue tient compte du zoom courant : divisée par lui, c'est la hauteur naturelle.
      const zoomCourant = Number(pieces.dataset.zoom) || 1;
      const naturelle = pieces.getBoundingClientRect().height / zoomCourant;
      setAjuste(
        zoomPourAjuster(boite.clientHeight - PADDING_VERTICAL, naturelle),
      );
    };
    mesurer();
    if (typeof ResizeObserver === "undefined") return;
    const observateur = new ResizeObserver(mesurer);
    observateur.observe(boite);
    observateur.observe(pieces);
    return () => observateur.disconnect();
  }, [mode]);

  return {
    mode,
    zoom: mode === "ajuste" ? ajuste : mode,
    setMode,
    conteneur,
    contenu,
  };
}
