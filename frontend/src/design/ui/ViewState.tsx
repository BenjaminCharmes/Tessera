import type { ReactNode } from "react";
import Button from "./Button";

/**
 * Les trois états d'une vue — ticket-439. Un vide dit quoi faire ensuite, un
 * chargement montre la forme du contenu, une erreur offre toujours une sortie.
 */
interface VideProps {
  titre: string;
  phrase: string;
  /** Ce qu'on peut faire ensuite, par exemple un bouton. */
  action?: ReactNode;
}

export function Vide({ titre, phrase, action }: VideProps) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
      <p className="text-corps font-semibold text-zinc-200">{titre}</p>
      <p className="max-w-sm text-xs text-zinc-400">{phrase}</p>
      {action}
    </div>
  );
}

interface ChargementProps {
  lignes?: number;
}

export function Chargement({ lignes = 3 }: ChargementProps) {
  return (
    <div role="status" aria-label="Chargement" className="py-1">
      {Array.from({ length: lignes }).map((_, i) => (
        <div key={i} className="mx-4 my-1 h-9 animate-pulse rounded-sm bg-zinc-800" />
      ))}
    </div>
  );
}

interface ErreurProps {
  message: string;
  onRetry: () => void;
}

export function Erreur({ message, onRetry }: ErreurProps) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 px-4 py-10 text-center">
      <p className="text-xs text-red-300">{message}</p>
      <Button variante="borde" onClick={onRetry}>
        Réessayer
      </Button>
    </div>
  );
}
