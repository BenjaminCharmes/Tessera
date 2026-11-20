import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, MouseEvent, ReactNode } from "react";

const FOCALISABLES =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
  'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Tab et Maj+Tab bouclent sur les éléments focalisables de la modale. */
function retenirLeFocus(e: KeyboardEvent<HTMLElement>, racine: HTMLElement) {
  if (e.defaultPrevented) return;
  const liste = Array.from(racine.querySelectorAll<HTMLElement>(FOCALISABLES));
  if (liste.length === 0) {
    e.preventDefault();
    return;
  }
  const premier = liste[0];
  const dernier = liste[liste.length - 1];
  const actif = document.activeElement;
  if (e.shiftKey && (actif === premier || actif === racine)) {
    e.preventDefault();
    dernier.focus();
  } else if (!e.shiftKey && actif === dernier) {
    e.preventDefault();
    premier.focus();
  }
}

/** À la fermeture, le focus retourne à l'élément qui a ouvert la modale, s'il existe encore. */
function rendreLeFocus(ouvrant: Element | null) {
  const actif = document.activeElement;
  const perdu = actif === null || actif === document.body;
  if (perdu && ouvrant instanceof HTMLElement && ouvrant.isConnected) ouvrant.focus();
}

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
 * agisse même sur une modale sans champ à remplir. Tab reste dans la modale, et
 * le focus retourne à ce qui l'a ouverte quand elle se ferme.
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
  // Ce qui avait le focus avant l'ouverture : lu au rendu, avant qu'un enfant en autoFocus ne le prenne.
  const [ouvrant] = useState<Element | null>(() => document.activeElement);

  useEffect(() => {
    const racine = ref.current;
    if (racine && !racine.contains(document.activeElement)) racine.focus();
    return () => rendreLeFocus(ouvrant);
  }, [ouvrant]);

  function surClic(e: MouseEvent<HTMLDivElement>) {
    if (isoler) e.stopPropagation();
    if (fermerSurLeFond && peutFermer && e.target === e.currentTarget) onFermer?.();
  }

  function surTouche(e: KeyboardEvent<HTMLDivElement>) {
    if (isoler) e.stopPropagation();
    if (e.key === "Escape" && peutFermer) onFermer?.();
    if (e.key === "Tab" && ref.current) retenirLeFocus(e, ref.current);
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

interface TitreDeModaleProps {
  children: ReactNode;
  id?: string;
  /** Marge seulement : le style du titre est le même partout. */
  className?: string;
}

/** Le titre d'une modale : un `<h2>` au style unique. */
export function TitreDeModale({ children, id, className = "" }: TitreDeModaleProps) {
  return (
    <h2 id={id} className={`text-base font-semibold text-zinc-100 ${className}`.trim()}>
      {children}
    </h2>
  );
}
