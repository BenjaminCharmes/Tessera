import { useEffect, useState, type FormEvent } from "react";
import { saisirJeton } from "../../lib/auth";
import { onJetonManquant } from "../../lib/http";
import Button from "../../design/ui/Button";

export const CHEMIN_JETON_WINDOWS = "%LOCALAPPDATA%\\Tessera\\jeton-de-session";
export const CHEMIN_JETON_AUTRE = "~/.local/state/tessera/jeton-de-session";

/**
 * Bandeau qui demande le jeton de session quand le backend répond 401
 * (ticket-877). La saisie va en `sessionStorage` et sert à la requête suivante ;
 * le champ se déclare mot de passe pour que le navigateur le garde dans son
 * coffre, jamais la page (ticket-951).
 */
export default function BandeauJeton() {
  const [visible, setVisible] = useState(false);
  const [valeur, setValeur] = useState("");

  useEffect(() => onJetonManquant(() => setVisible(true)), []);

  if (!visible) return null;

  function valider(evenement: FormEvent<HTMLFormElement>): void {
    evenement.preventDefault();
    if (!valeur.trim()) return;
    saisirJeton(valeur);
    setValeur("");
    setVisible(false);
  }

  return (
    <form
      role="alert"
      onSubmit={valider}
      className="fixed inset-x-0 top-0 z-50 flex flex-wrap items-center gap-3 border-b border-amber-700 bg-amber-950 px-4 py-2 text-sm text-amber-100"
    >
      {/* Identifiant fixe : le gestionnaire de mots de passe du navigateur range
          le jeton sous « tessera » et le remplit au prochain onglet (ticket-951). */}
      <input
        type="text"
        name="username"
        autoComplete="username"
        value="tessera"
        readOnly
        tabIndex={-1}
        aria-hidden="true"
        className="sr-only"
      />
      <label htmlFor="jeton-de-session" className="font-medium">
        Jeton de session
      </label>
      <input
        id="jeton-de-session"
        name="password"
        type="password"
        autoComplete="current-password"
        value={valeur}
        onChange={(e) => setValeur(e.target.value)}
        className="min-w-64 rounded border border-zinc-600 bg-zinc-900 px-2 py-1 text-zinc-100"
      />
      <Button type="submit" variante="plein" taille="compact">
        Valider
      </Button>
      <span className="text-xs text-amber-200">
        Avec <code>STATIC_TOKEN</code> défini, c'est sa valeur. Sinon, le backend
        l'écrit dans <code>{CHEMIN_JETON_WINDOWS}</code> (Windows) ou{" "}
        <code>{CHEMIN_JETON_AUTRE}</code>. Gardé jusqu'à la fermeture de l'onglet ; enregistre-le dans le
        navigateur pour qu'il se remplisse seul.
      </span>
    </form>
  );
}
