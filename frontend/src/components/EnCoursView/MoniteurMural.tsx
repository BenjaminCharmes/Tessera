import type { ReactNode } from "react";

/** Une ligne affichée sur l'écran, avec sa classe de ton (ADR-026). */
export interface LigneDEcran {
  cle: string | number;
  texte: string;
  ton: string;
}

interface MoniteurMuralProps {
  titre: string;
  /** Ce que dit le coin droit du bandeau : un état, un compte. */
  statut: ReactNode;
  lignes: readonly LigneDEcran[];
  /** Classe du voyant du cadre ; il dit l'état de ce que l'écran montre. */
  voyant: string;
  vide?: string;
  /** Un écran cliquable (journal d'un service) : bouton, avec son état déplié. */
  onClick?: () => void;
  deplie?: boolean;
  controle?: string;
  data?: Record<`data-${string}`, string>;
}

const CADRE =
  "w-full rounded-[3px] border-4 border-b-[10px] bg-zinc-950 text-left shadow-[0_4px_0_rgb(0_0_0/0.35)]";

/**
 * Le moniteur accroché au mur d'une salle — tickets 711 et 726 : support, cadre,
 * bandeau, quelques lignes et un voyant. Les écrans des services et ceux de la
 * salle Tessera partagent ce dessin ; seul ce qu'ils montrent change.
 */
export default function MoniteurMural({
  titre, statut, lignes, voyant, vide = "(rien à montrer)", onClick, deplie = false, controle, data,
}: MoniteurMuralProps) {
  const contenu = (
    <>
      <span className="flex justify-between gap-2 bg-zinc-900 px-2 py-0.5 font-mono text-micro text-zinc-400">
        <span className="truncate">{titre}</span>
        <span className="shrink-0">{statut}</span>
      </span>
      <span className="block h-[5.6rem] overflow-hidden px-2 py-1 font-mono text-micro leading-[1.1rem]">
        {lignes.length === 0 ? (
          <span className="block text-zinc-600">{vide}</span>
        ) : (
          lignes.map((ligne) => (
            <span key={ligne.cle} className={`block truncate ${ligne.ton}`}>
              {ligne.texte || " "}
            </span>
          ))
        )}
      </span>
    </>
  );
  return (
    <div className="flex min-w-0 flex-col items-center">
      <span aria-hidden="true" className="h-2 w-10 bg-zinc-600" />
      {onClick ? (
        <button
          type="button"
          onClick={onClick}
          aria-expanded={deplie}
          aria-controls={controle}
          title={deplie ? "Replier" : "Déplier"}
          className={`${CADRE} ${deplie ? "border-violet-600" : "border-zinc-700"} hover:border-violet-600 focus-visible:border-violet-600 focus-visible:outline-none`}
          {...data}
        >
          {contenu}
        </button>
      ) : (
        <div className={`${CADRE} border-zinc-700`} {...data}>
          {contenu}
        </div>
      )}
      <span aria-hidden="true" className={`-mt-[7px] size-1 rounded-full ${voyant}`} />
    </div>
  );
}
