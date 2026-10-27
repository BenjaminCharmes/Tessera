import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { positionInfobulle } from "../../lib/bureau/positionInfobulle";
import type { PositionFixe, Rectangle } from "../../lib/bureau/positionInfobulle";

interface InfobulleProps {
  id: string;
  ancre: Rectangle;
  children: ReactNode;
}

/**
 * La boîte de l'infobulle, rendue dans `document.body` : la pièce coupe ce qui
 * déborde (`overflow-hidden`). Elle se place sur l'ancre, une fois sa taille connue.
 */
function Infobulle({ id, ancre, children }: InfobulleProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<PositionFixe>({ top: ancre.top, left: ancre.left });

  // Mesurée avant la peinture : la position finale dépend de la taille réelle de l'infobulle.
  useLayoutEffect(() => {
    const boite = ref.current;
    if (!boite) return;
    const mesure = { largeur: boite.offsetWidth, hauteur: boite.offsetHeight };
    const suivante = positionInfobulle(ancre, mesure, { largeur: window.innerWidth, hauteur: window.innerHeight });
    // Les enfants changent d'identité à chaque rendu : une position inchangée ne relance rien.
    setPosition((p) => (p.top === suivante.top && p.left === suivante.left ? p : suivante));
  }, [ancre, children]);

  return createPortal(
    <div
      id={id}
      ref={ref}
      role="tooltip"
      style={{ top: position.top, left: position.left }}
      className="pointer-events-none fixed z-50 w-max max-w-72 rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-200"
    >
      {children}
    </div>,
    document.body,
  );
}

interface AvecInfobulleProps {
  /** Le nom accessible de l'objet. */
  label: string;
  className: string;
  /** Le contenu de l'infobulle, montré au survol ou au focus. */
  infobulle: ReactNode;
  /** Un clic, ou Entrée ou Espace au clavier : l'objet devient un bouton (ticket-602). */
  onActiver?: () => void;
  children: ReactNode;
}

/**
 * Un objet de la pièce focusable, avec son infobulle au survol et au focus.
 * L'ancre est le rectangle de l'objet à l'ouverture : l'infobulle se place dessus.
 */
export default function AvecInfobulle({ label, className, infobulle, onActiver, children }: AvecInfobulleProps) {
  const [ancre, setAncre] = useState<Rectangle | null>(null);
  const racine = useRef<HTMLDivElement>(null);
  const idInfobulle = useId();
  const ouvrir = () => setAncre(racine.current?.getBoundingClientRect() ?? null);
  const fermer = () => setAncre(null);

  // Une position fixe ne suit pas le défilement : l'infobulle se referme plutôt que de rester à côté.
  useEffect(() => {
    if (ancre === null) return;
    const refermer = () => setAncre(null);
    window.addEventListener("scroll", refermer, true);
    return () => window.removeEventListener("scroll", refermer, true);
  }, [ancre]);

  return (
    <div
      ref={racine}
      role={onActiver ? "button" : "group"}
      tabIndex={0}
      aria-label={label}
      aria-describedby={ancre ? idInfobulle : undefined}
      className={onActiver ? `${className} cursor-pointer` : className}
      onClick={onActiver}
      onKeyDown={
        onActiver &&
        ((e) => {
          if (e.target !== e.currentTarget) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onActiver();
          }
        })
      }
      onMouseEnter={ouvrir}
      onMouseLeave={fermer}
      onFocus={ouvrir}
      onBlur={fermer}
    >
      {ancre && (
        <Infobulle id={idInfobulle} ancre={ancre}>
          {infobulle}
        </Infobulle>
      )}
      {children}
    </div>
  );
}
