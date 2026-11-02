import { useEffect, useRef } from "react";
import type { KeyboardEvent, MouseEvent, ReactNode } from "react";

interface ModaleProps {
  children: ReactNode;
  /**
   * Ferme la modale (touche Escape, clic sur le fond). Absent, la modale ne se
   * ferme pas d'elle-même : seul son contenu la retire.
   */
  onFermer?: () => void;
  /** Suspend Escape et le clic sur le fond : travail en cours, rien à jeter. */
  fermetureSuspendue?: boolean;
  /** Un clic sur le fond ferme ; à couper pour une confirmation destructive. */
  fermerSurLeFond?: boolean;
  /** Arrête clics et touches au fond : la modale est rendue sous un parent cliquable. */
  isoler?: boolean;
  /** Teinte du fond, en classe Tailwind littérale. */
  fond?: string;
  /** Classes ajoutées au fond (marge, par exemple). */
  className?: string;
  "aria-label"?: string;
  "aria-labelledby"?: string;
}

/**
 * Fond, `role="dialog"`, `aria-modal` et fermeture par Escape, à un seul endroit.
 *
 * Le fond porte le rôle `dialog` : c'est lui qui reçoit Escape et le clic.
 * Il prend le focus à l'ouverture si rien dedans ne l'a pris, pour qu'Escape
 * agisse même sur une modale sans champ à remplir.
 */
export default function Modale({
  children,
  onFermer,
  fermetureSuspendue = false,
  fermerSurLeFond = true,
  isoler = false,
  fond = "bg-black/60",
  className = "",
  ...aria
}: ModaleProps) {
  const ref = useRef<HTMLDivElement>(null);
  const peutFermer = onFermer !== undefined && !fermetureSuspendue;

  useEffect(() => {
    const racine = ref.current;
    if (racine && !racine.contains(document.activeElement)) racine.focus();
  }, []);

  function surClic(e: MouseEvent<HTMLDivElement>) {
    if (isoler) e.stopPropagation();
    if (fermerSurLeFond && peutFermer && e.target === e.currentTarget) onFermer?.();
  }

  function surTouche(e: KeyboardEvent<HTMLDivElement>) {
    if (isoler) e.stopPropagation();
    if (e.key === "Escape" && peutFermer) onFermer?.();
  }

  return (
    <div
      ref={ref}
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      aria-label={aria["aria-label"]}
      aria-labelledby={aria["aria-labelledby"]}
      onClick={surClic}
      onKeyDown={surTouche}
      className={`fixed inset-0 z-50 flex items-center justify-center focus:outline-hidden ${fond} ${className}`.trim()}
    >
      {children}
    </div>
  );
}
