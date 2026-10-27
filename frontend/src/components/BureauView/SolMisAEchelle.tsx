import { useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { echelleDuSol } from "../../lib/bureau/echelleDuSol";

/**
 * Le sol garde son repère de 800 px, où se calculent les positions des agents :
 * il est rendu agrandi ou réduit pour remplir la largeur de la salle. `zoom`
 * (et non `transform: scale`) change la place prise dans le flux : la salle
 * suivante ne chevauche pas. Au-delà de la borne haute, le sol se centre.
 */
export default function SolMisAEchelle({ children }: { children: ReactNode }) {
  const conteneur = useRef<HTMLDivElement>(null);
  const [echelle, setEchelle] = useState(1);

  useLayoutEffect(() => {
    const boite = conteneur.current;
    if (!boite) return;
    // Une largeur nulle (conteneur masqué, jsdom) n'est pas une mesure : l'échelle reste à 1.
    const appliquer = (largeur: number) => {
      if (largeur > 0) setEchelle(echelleDuSol(largeur));
    };
    appliquer(boite.clientWidth);
    if (typeof ResizeObserver === "undefined") return;
    const observateur = new ResizeObserver(([entree]) => {
      if (entree) appliquer(entree.contentRect.width);
    });
    observateur.observe(boite);
    return () => observateur.disconnect();
  }, []);

  return (
    <div ref={conteneur} className="flex">
      <div data-echelle={echelle} style={{ zoom: echelle }} className="relative mx-auto w-200 shrink-0">
        {children}
      </div>
    </div>
  );
}
