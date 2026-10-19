import StatusPill from "../../design/ui/StatusPill";
import type { EtapeMiseEnLigne } from "../../types/api";
import { ETATS, nomDEtape } from "./etapes";

/** Un échec se lit en rouge dans la colonne de détail ; le reste en gris (maquette). */
function classeDuDetail(etape: EtapeMiseEnLigne): string {
  return etape.state === "failed" ? "text-red-300" : "text-zinc-400";
}

/**
 * Le déroulé des étapes — ticket-472, maquette « déroulé des étapes ».
 *
 * Le `detail` de chaque étape se lit en entier, `manual` et `needs_human`
 * compris : c'est lui qui dit quoi poser, supprimer ou créer. Il ne porte
 * jamais de secret (le plan masque ce qui sort d'une étape, ADR-053).
 */
export default function ListeDesEtapes({ etapes }: { etapes: EtapeMiseEnLigne[] }) {
  return (
    <ol aria-label="Étapes de la mise en ligne" className="divide-y divide-zinc-800">
      {etapes.map((etape, i) => {
        const etat = ETATS[etape.state];
        return (
          <li
            key={etape.step}
            data-etape={etape.step}
            data-etat-etape={etape.state}
            className="flex items-start gap-3 py-2.5"
          >
            <span className="w-5 shrink-0 pt-0.5 text-xs text-zinc-500">{i + 1}</span>
            <div className="min-w-0 flex-1">
              <p className="text-corps text-zinc-100">{nomDEtape(etape.step)}</p>
              {etape.detail && (
                <p className={`mt-0.5 text-xs leading-snug ${classeDuDetail(etape)}`}>
                  {etape.detail}
                </p>
              )}
            </div>
            <StatusPill etat={etat.pastille} libelle={etat.libelle} />
          </li>
        );
      })}
    </ol>
  );
}
