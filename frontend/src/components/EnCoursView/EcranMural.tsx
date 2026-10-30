import type { ServiceActif } from "../../types/api";
import { etatDuService, libelleDeLEtat } from "../../design/etatDuService";
import { niveauDeLigne, TON_DE_LIGNE } from "./journal";

interface EcranMuralProps {
  service: ServiceActif;
  /** Le journal de ce service est ouvert sous la salle. */
  deplie: boolean;
  /** Ouvre le journal, ou le referme s'il est déjà ouvert. */
  onBasculer: () => void;
}

const LIGNES_VISIBLES = 5;

const TON_ETAT = {
  "en-cours": "text-green-300",
  echoue: "text-red-300",
  arrete: "text-zinc-400",
  "jamais-lance": "text-zinc-500",
} as const;

const VOYANT = {
  "en-cours": "bg-green-500",
  echoue: "bg-red-500",
  arrete: "bg-zinc-600",
  "jamais-lance": "bg-zinc-700",
} as const;

/**
 * Le moniteur accroché au mur pour un service lancé par l'IDE — ticket-711. Il
 * montre les dernières lignes que le backend a gardées (`sortie`) ; un clic ouvre
 * le journal complet sous la salle, un second le referme. Le voyant du cadre dit l'état du service (ADR-058).
 */
export default function EcranMural({ service, deplie, onBasculer }: EcranMuralProps) {
  const sortie = service.sortie ?? [];
  const lignes = sortie.slice(-LIGNES_VISIBLES);
  const etat = etatDuService(service);
  return (
    <div className="flex min-w-0 flex-col items-center">
      <span aria-hidden="true" className="h-2 w-10 bg-zinc-600" />
      <button
        type="button"
        onClick={onBasculer}
        aria-expanded={deplie}
        aria-controls={`journal-${service.project_id}-${service.nom}`}
        data-ecran-mural={service.nom}
        title={deplie ? "Replier le journal" : "Déplier le journal"}
        className={`w-full rounded-[3px] border-4 border-b-[10px] ${deplie ? "border-violet-600" : "border-zinc-700"} bg-zinc-950 text-left shadow-[0_4px_0_rgb(0_0_0/0.35)] hover:border-violet-600 focus-visible:border-violet-600 focus-visible:outline-none`}
      >
        <span className="flex justify-between bg-zinc-900 px-2 py-0.5 font-mono text-micro text-zinc-400">
          <span>{service.nom}</span>
          <span className={TON_ETAT[etat]}>{libelleDeLEtat(service)}</span>
        </span>
        <span className="block h-[5.6rem] overflow-hidden px-2 py-1 font-mono text-micro leading-[1.1rem]">
          {lignes.length === 0 ? (
            <span className="block text-zinc-600">(rien d'écrit pour l'instant)</span>
          ) : (
            lignes.map((ligne, i) => (
              <span
                key={sortie.length - lignes.length + i}
                className={`block truncate ${TON_DE_LIGNE[niveauDeLigne(ligne)]}`}
              >
                {ligne || " "}
              </span>
            ))
          )}
        </span>
      </button>
      <span aria-hidden="true" className={`-mt-[7px] size-1 rounded-full ${VOYANT[etat]}`} />
    </div>
  );
}
