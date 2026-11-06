import { useEffect, useState, type FormEvent } from "react";
import { saisirJeton } from "../../lib/auth";
import { onJetonManquant } from "../../lib/http";

export const CHEMIN_JETON_WINDOWS = "%LOCALAPPDATA%\\Tessera\\jeton-de-session";
export const CHEMIN_JETON_AUTRE = "~/.local/state/tessera/jeton-de-session";

/**
 * Bandeau qui demande le jeton de session quand le backend répond 401
 * (ticket-877). La saisie va en `sessionStorage` et sert à la requête suivante.
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
      <label htmlFor="jeton-de-session" className="font-medium">
        Jeton de session
      </label>
      <input
        id="jeton-de-session"
        type="password"
        autoComplete="off"
        value={valeur}
        onChange={(e) => setValeur(e.target.value)}
        className="min-w-64 rounded border border-zinc-600 bg-zinc-900 px-2 py-1 text-zinc-100"
      />
      <button type="submit" className="rounded bg-violet-600 px-3 py-1 text-white hover:bg-violet-500">
        Valider
      </button>
      <span className="text-xs text-amber-200">
        Le backend l'écrit dans <code>{CHEMIN_JETON_WINDOWS}</code> (Windows) ou{" "}
        <code>{CHEMIN_JETON_AUTRE}</code>.
      </span>
    </form>
  );
}
