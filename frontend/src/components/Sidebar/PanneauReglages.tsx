import { useReglages } from "../../hooks/useReglages";
import LigneDeReglage from "./LigneDeReglage";

/**
 * Les cinq réglages globaux (ADR-075, ticket-810) : ce qu'on change ici vaut
 * pour les prochains runs ; un run ouvert garde la valeur avec laquelle il a
 * démarré. Aucun secret, aucun réglage par projet.
 */
export default function PanneauReglages() {
  const { liste, chargement, erreur, ecrire, retirer } = useReglages();
  return (
    <div>
      <p className="border-b border-zinc-800 px-3 py-2 text-micro text-zinc-400">
        Réglages globaux · valeur du prochain run
      </p>
      {erreur ? (
        <p role="alert" className="px-3 py-2 text-micro text-red-400">
          {erreur}
        </p>
      ) : null}
      {chargement ? <p className="px-3 py-2 text-micro text-zinc-500">Chargement…</p> : null}
      <ul aria-label="Réglages">
        {liste.map((r) => (
          <LigneDeReglage
            key={`${r.nom}-${String(r.valeur)}-${r.modifie}`}
            reglage={r}
            onEcrire={ecrire}
            onRetirer={retirer}
          />
        ))}
      </ul>
    </div>
  );
}
