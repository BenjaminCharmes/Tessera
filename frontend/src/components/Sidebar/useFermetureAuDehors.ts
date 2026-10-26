import { useEffect, useRef, type RefObject } from "react";

/**
 * Referme un panneau ouvert sur Échap ou sur un clic en dehors de son
 * conteneur — partagé par les réglages et la cloche du rail.
 */
export function useFermetureAuDehors(
  ouvert: boolean,
  fermer: () => void,
): RefObject<HTMLDivElement | null> {
  const conteneur = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ouvert) return;
    function surTouche(e: KeyboardEvent) {
      if (e.key === "Escape") fermer();
    }
    function surClic(e: MouseEvent) {
      if (!conteneur.current?.contains(e.target as Node)) fermer();
    }
    document.addEventListener("keydown", surTouche);
    document.addEventListener("mousedown", surClic);
    return () => {
      document.removeEventListener("keydown", surTouche);
      document.removeEventListener("mousedown", surClic);
    };
  }, [ouvert, fermer]);

  return conteneur;
}
