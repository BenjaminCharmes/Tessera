import { useState } from "react";

/**
 * Parler à l'agent pendant qu'il travaille (ticket-066).
 *
 * Deux choses distinctes, et il importe qu'elles le restent à l'écran :
 *
 * - **la question de l'agent**, qui suspend le run et attend une réponse ;
 * - **la consigne spontanée**, qui n'attend rien et sera lue par le prochain
 *   agent à parler.
 *
 * Les confondre ferait passer un « au fait, pense aux tests » pour la réponse
 * à « on casse l'API ? ». Le backend les sépare déjà ; l'interface doit le
 * montrer, sans quoi l'utilisateur les mélangera pour lui.
 *
 * Hors run, le composant disparaît : il n'y a personne à qui parler, et un
 * champ de saisie laisserait croire le contraire.
 */
interface AgentDialogueProps {
  pendingQuestion: string | null;
  enCours: boolean;
  onAnswer: (text: string) => void;
  onInterject: (text: string) => void;
}

export default function AgentDialogue({
  pendingQuestion,
  enCours,
  onAnswer,
  onInterject,
}: AgentDialogueProps) {
  const [reponse, setReponse] = useState("");
  const [consigne, setConsigne] = useState("");

  if (!enCours) return null;

  function envoyerReponse() {
    const texte = reponse.trim();
    if (!texte) return;
    onAnswer(texte);
    setReponse("");
  }

  function envoyerConsigne() {
    const texte = consigne.trim();
    if (!texte) return;
    onInterject(texte);
    setConsigne("");
  }

  return (
    <div className="border-t border-zinc-800 bg-zinc-900 px-3 py-2.5">
      {pendingQuestion ? (
        <div className="mb-3">
          <p className="mb-1 text-micro uppercase tracking-wide text-amber-500">
            L'agent attend votre réponse
          </p>
          <p className="mb-2 rounded border border-amber-900/60 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-100">
            {pendingQuestion}
          </p>
          <label
            htmlFor="dialogue-reponse"
            className="mb-1 block text-mini text-zinc-400"
          >
            Votre réponse
          </label>
          <div className="flex gap-1.5">
            <input
              id="dialogue-reponse"
              value={reponse}
              onChange={(e) => setReponse(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && envoyerReponse()}
              className="min-w-0 flex-1 rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-100 outline-none focus:border-zinc-500"
            />
            <button
              type="button"
              onClick={envoyerReponse}
              className="rounded bg-amber-700 px-2 py-1 text-xs text-amber-50 transition-colors hover:bg-amber-600"
            >
              Répondre
            </button>
          </div>
        </div>
      ) : null}

      <label
        htmlFor="dialogue-consigne"
        className="mb-1 block text-mini text-zinc-500"
      >
        Consigne pour le prochain tour
      </label>
      <div className="flex gap-1.5">
        <input
          id="dialogue-consigne"
          value={consigne}
          onChange={(e) => setConsigne(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && envoyerConsigne()}
          placeholder="lue par le prochain agent à parler"
          className="min-w-0 flex-1 rounded border border-zinc-800 bg-zinc-950 px-2 py-1 text-xs text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-zinc-600"
        />
        <button
          type="button"
          onClick={envoyerConsigne}
          className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300 transition-colors hover:border-zinc-500 hover:text-zinc-100"
        >
          Envoyer
        </button>
      </div>
    </div>
  );
}
