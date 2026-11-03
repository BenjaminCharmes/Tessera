import { useLayoutEffect, useState } from "react";
import { useEtatPersistant } from "./useEtatPersistant";
import { estModeDeZoom, zoomPourAjuster, zoomPourLignes } from "../lib/bureau/zoomDuBureau";
import type { ModeDeZoom } from "../lib/bureau/zoomDuBureau";

/** Le padding vertical du conteneur qui défile (`p-3`) : il ne reçoit pas de pièce. */
const PADDING_VERTICAL = 24;

interface OptionsDuZoom {
  /** La clé de mémorisation : chaque vue garde son zoom. */
  cle?: string;
  /** Le padding horizontal du conteneur, hors de la mise en page de référence. */
  margeHorizontale?: number;
  /**
   * Le nombre de lignes (`[data-ligne-du-zoom]`) que le zoom par défaut fait tenir
   * exactement dans la hauteur ; sans lui, le zoom par défaut est 100 %.
   */
  lignes?: number;
}

/** La hauteur, depuis le haut du contenu, jusqu'au bas de sa `n`-ième ligne (la dernière s'il en a moins). */
function hauteurDesLignes(contenu: HTMLElement, n: number): number {
  const lignes = [...contenu.querySelectorAll<HTMLElement>("[data-ligne-du-zoom]")];
  const derniere = lignes[Math.min(n, lignes.length) - 1];
  if (!derniere) return contenu.getBoundingClientRect().height;
  return derniere.getBoundingClientRect().bottom - contenu.getBoundingClientRect().top;
}

/**
 * Le zoom d'une vue de sprites et ce qu'il faut pour le mesurer — ticket-657,
 * ticket-727. Le mode est mémorisé ; « ajusté » fait tenir tout le contenu, « lignes »
 * ses premières lignes, et l'un comme l'autre se recalcule quand la vue ou son
 * contenu change de taille. `largeur` est la mise en page de référence : posée sur le
 * contenu zoomé, elle le fait grandir comme un bloc (avec un défilement de côté au-delà
 * de 100 %) au lieu de réagencer les salles.
 */
export function useZoomDuBureau({ cle = "bureau.zoom.v2", lignes, margeHorizontale = 24 }: OptionsDuZoom = {}) {
  const defaut: ModeDeZoom = lignes ? "lignes" : 1;
  const [mode, setMode] = useEtatPersistant<ModeDeZoom>(cle, defaut, estModeDeZoom);
  // Des refs-callback qui tiennent le nœud en état : la vue monte ses pièces après coup
  // (connexion, chargement, bascule de vue), et chaque montage relance la mesure.
  const [boite, conteneur] = useState<HTMLDivElement | null>(null);
  const [pieces, contenu] = useState<HTMLDivElement | null>(null);
  const [mesure, setMesure] = useState(1);
  const [largeur, setLargeur] = useState<number | null>(null);

  // La mise en page de référence : la largeur du conteneur, à 100 %. Le contenu la garde à
  // tout zoom, qui l'agrandit ou la réduit d'un bloc ; rien ne se réagence (ticket-727).
  useLayoutEffect(() => {
    if (!boite) return;
    const mesurer = () => {
      const l = boite.clientWidth - margeHorizontale;
      setLargeur(l > 0 ? l : null);
    };
    mesurer();
    if (typeof ResizeObserver === "undefined") return;
    const observateur = new ResizeObserver(mesurer);
    observateur.observe(boite);
    return () => observateur.disconnect();
  }, [boite, margeHorizontale]);

  useLayoutEffect(() => {
    if (mode !== "ajuste" && mode !== "lignes") return;
    if (!boite || !pieces) return;
    const mesurer = () => {
      // La hauteur rendue tient compte du zoom courant : divisée par lui, c'est la hauteur naturelle.
      const zoomCourant = Number(pieces.dataset.zoom) || 1;
      const dispo = boite.clientHeight - PADDING_VERTICAL;
      if (mode === "lignes" && lignes) {
        // Jamais au-delà de 100 % : la mise en page de référence déborderait sur le côté.
        setMesure(Math.min(1, zoomPourLignes(dispo, hauteurDesLignes(pieces, lignes) / zoomCourant)));
      } else {
        setMesure(zoomPourAjuster(dispo, pieces.getBoundingClientRect().height / zoomCourant));
      }
    };
    mesurer();
    if (typeof ResizeObserver === "undefined") return;
    const observateur = new ResizeObserver(mesurer);
    observateur.observe(boite);
    observateur.observe(pieces);
    return () => observateur.disconnect();
  }, [mode, lignes, boite, pieces]);

  return {
    mode,
    defaut,
    zoom: typeof mode === "number" ? mode : mesure,
    largeur,
    setMode,
    conteneur,
    contenu,
  };
}
