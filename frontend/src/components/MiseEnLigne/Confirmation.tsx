import Button from "../../design/ui/Button";
import StatusPill from "../../design/ui/StatusPill";
import type { StripeMode } from "../../types/api";
import Fenetre from "./Fenetre";

interface ConfirmationProps {
  nom: string;
  domaine: string | null;
  /** `null` : le projet ne déclare pas de Stripe. */
  modeStripe: StripeMode | null;
  onConfirmer: () => void;
  onAnnuler: () => void;
}

/** Le mode Stripe, nommé : le réel se voit, il ne s'active qu'à la main. */
export function PastilleStripe({ mode }: { mode: StripeMode }) {
  return mode === "live" ? (
    <StatusPill etat="echec" libelle="Stripe live" />
  ) : (
    <StatusPill etat="attention" libelle="Stripe test" />
  );
}

const GARANTIES = [
  "Tessera crée ce qui manque et garde ce qui existe. Il ne supprime rien.",
  "Les jetons restent dans le backend : aucun agent ne les voit.",
  "Le mode réel de Stripe ne s'active qu'à la main.",
];

/**
 * La confirmation avant la mise en ligne — ticket-472, maquette « carte et
 * confirmation ». Elle nomme le domaine et le mode Stripe : rien n'est appelé
 * tant que l'utilisateur n'a pas confirmé.
 */
export default function Confirmation({
  nom,
  domaine,
  modeStripe,
  onConfirmer,
  onAnnuler,
}: ConfirmationProps) {
  return (
    <Fenetre
      idTitre="titre-confirmation-mise-en-ligne"
      bandeau="Mettre en ligne"
      pied={
        <>
          <Button variante="discret" onClick={onAnnuler}>
            Annuler
          </Button>
          <Button variante="plein" onClick={onConfirmer}>
            Mettre en ligne
          </Button>
        </>
      }
    >
      <h2
        id="titre-confirmation-mise-en-ligne"
        className="text-xl font-semibold text-zinc-100"
      >
        Mettre {nom} en ligne ?
      </h2>
      <dl className="grid grid-cols-[6rem_1fr] items-center gap-y-2.5">
        <dt className="text-micro text-zinc-400">Domaine</dt>
        <dd className="font-mono text-corps text-zinc-100">{domaine ?? "non déclaré"}</dd>
        {modeStripe && (
          <>
            <dt className="text-micro text-zinc-400">Paiements</dt>
            <dd className="flex items-center gap-2">
              <PastilleStripe mode={modeStripe} />
              <span className="text-xs text-zinc-400">
                {modeStripe === "live" ? "paiements réels" : "aucun vrai paiement"}
              </span>
            </dd>
          </>
        )}
      </dl>
      <ul className="flex flex-col gap-1.5 rounded-md border border-zinc-800 bg-zinc-950 p-3 text-xs leading-snug text-zinc-400">
        {GARANTIES.map((g) => (
          <li key={g}>{g}</li>
        ))}
      </ul>
    </Fenetre>
  );
}
