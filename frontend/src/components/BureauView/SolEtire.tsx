import { useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { EtirementDuSol, MarcheActive } from "../../hooks/useEtirementDuSol";
import { etirementDuSol } from "../../lib/bureau/etirementDuSol";

/**
 * Le sol de la pièce, sur toute sa largeur. Les sprites gardent leur taille, celle
 * des salles communes : seules les abscisses du repère de 800 px s'étirent, pour
 * que les agents restent devant leur poste quand la grille s'élargit.
 */
export default function SolEtire({ children }: { children: ReactNode }) {
  const conteneur = useRef<HTMLDivElement>(null);
  const [etirement, setEtirement] = useState(1);
  const [marche, setMarche] = useState(false);

  useLayoutEffect(() => {
    const boite = conteneur.current;
    if (!boite) return;
    let courant = 1;
    // La marche ne s'active qu'après une image peinte à la bonne place (ticket-638).
    let image = requestAnimationFrame(() => setMarche(true));
    // Une largeur nulle (conteneur masqué, jsdom) n'est pas une mesure : l'étirement reste à 1.
    const appliquer = (largeur: number) => {
      if (largeur <= 0) return;
      const suivant = etirementDuSol(largeur);
      if (suivant === courant) return;
      courant = suivant;
      setEtirement(suivant);
      // Un sol qui change de largeur (zoom, « Ajuster » qui se mesure après le
      // montage, fenêtre redimensionnée) déplace les agents d'un coup : couper la
      // marche le temps d'une image, sinon ils glissent jusqu'à leur poste (ticket-720).
      setMarche(false);
      cancelAnimationFrame(image);
      image = requestAnimationFrame(() => setMarche(true));
    };
    appliquer(boite.clientWidth);
    if (typeof ResizeObserver === "undefined")
      return () => cancelAnimationFrame(image);
    const observateur = new ResizeObserver(([entree]) => {
      if (entree) appliquer(entree.contentRect.width);
    });
    observateur.observe(boite);
    return () => {
      cancelAnimationFrame(image);
      observateur.disconnect();
    };
  }, []);

  return (
    <div
      ref={conteneur}
      data-etirement={etirement}
      className="relative w-full min-w-150"
    >
      <EtirementDuSol.Provider value={etirement}>
        <MarcheActive.Provider value={marche}>{children}</MarcheActive.Provider>
      </EtirementDuSol.Provider>
    </div>
  );
}
