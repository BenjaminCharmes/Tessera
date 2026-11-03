import Button from "../../design/ui/Button";
import type { EtapeMiseEnLigne, StripeMode } from "../../types/api";
import { PastilleStripe } from "./Confirmation";
import Fenetre from "./Fenetre";
import ListeDesEtapes from "./ListeDesEtapes";

interface DerouleProps {
  nom: string;
  domaine: string | null;
  modeStripe: StripeMode | null;
  etapes: EtapeMiseEnLigne[];
  enCours: boolean;
  erreur: string | null;
  onFermer: () => void;
  onRelancer: () => void;
}

/** La phrase au-dessus des étapes : ce qui s'est passé, jamais plus que ce qu'on sait. */
function resume(etapes: EtapeMiseEnLigne[], enCours: boolean): string {
  if (enCours) return "Mise en ligne en cours. Tu peux fermer cette fenêtre : elle continue.";
  if (etapes.some((e) => e.state === "failed")) {
    return "Une étape a échoué : les suivantes n'ont pas été lancées. Ce qui est fait reste fait — corrige, puis relance.";
  }
  if (etapes.some((e) => e.state === "manual" || e.state === "needs_human")) {
    return "Des étapes t'attendent. Fais-les, puis relance : seules celles qui manquent sont rejouées.";
  }
  return "Chaque étape a rendu son état.";
}

/**
 * Le déroulé de la mise en ligne — ticket-472, maquette « déroulé des étapes ».
 * « Relancer » relit chaque service et ne crée que ce qui manque.
 */
export default function Deroule({
  nom,
  domaine,
  modeStripe,
  etapes,
  enCours,
  erreur,
  onFermer,
  onRelancer,
}: DerouleProps) {
  return (
    <Fenetre
      idTitre="titre-deroule-mise-en-ligne"
      bandeau="Mise en ligne"
      pied={
        <>
          <Button variante="discret" onClick={onFermer}>
            Fermer
          </Button>
          <Button variante="plein" disabled={enCours} onClick={onRelancer}>
            Relancer
          </Button>
        </>
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="titre-deroule-mise-en-ligne" className="text-xl font-semibold text-zinc-100">
          {nom}
        </h2>
        {domaine && <span className="font-mono text-xs text-zinc-300">{domaine}</span>}
        {modeStripe && <PastilleStripe mode={modeStripe} />}
      </div>
      <p className="text-xs text-zinc-400">{resume(etapes, enCours)}</p>
      {erreur && (
        <p role="alert" className="rounded-md border border-red-500/35 bg-red-500/10 px-3 py-2 text-xs text-red-200">
          {erreur}
        </p>
      )}
      <ListeDesEtapes etapes={etapes} />
    </Fenetre>
  );
}
