import { useEffect, useState } from "react";
import CompteARebours from "./CompteARebours";

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
  /** Quand l'agent reprendra seul, s'il l'a annoncé (ticket-186). */
  questionExpireA?: string | null;
  enCours: boolean;
  onAnswer: (text: string) => void;
  onInterject: (text: string) => void;
  onStop: () => void;
  /** Accusé de réception de la dernière réponse envoyée (ticket-320). */
  answerAck?: "transmitted" | "deposited" | null;
}

export default function AgentDialogue({
  pendingQuestion,
  questionExpireA = null,
  enCours,
  onAnswer,
  onInterject,
  onStop,
  answerAck = null,
}: AgentDialogueProps) {
  const [reponse, setReponse] = useState("");
  const [consigne, setConsigne] = useState("");

  // Même patron que CompteARebours : la valeur initiale est capturée dans le
  // lazy initializer — autorisé par react-hooks/purity — puis mise à jour par
  // l'intervalle quand une échéance est active.
  const [maintenant, setMaintenant] = useState(() => Date.now());
  useEffect(() => {
    if (!questionExpireA || !pendingQuestion) return;
    const echeance = Date.parse(questionExpireA);
    if (Number.isNaN(echeance) || maintenant >= echeance) return;
    const t = setInterval(() => {
      setMaintenant(Date.now());
      if (Date.now() >= echeance) clearInterval(t);
    }, 1000);
    return () => clearInterval(t);
  }, [questionExpireA, pendingQuestion, maintenant]);

  if (!enCours) return null;

  // Une question expirée n'attend plus de réponse : l'agent a repris seul.
  const isExpired =
    questionExpireA !== null &&
    pendingQuestion !== null &&
    maintenant > new Date(questionExpireA).getTime();

  // Heure d'expiration lisible : « 13:14 » en heure locale.
  const expireLabel = questionExpireA
    ? new Date(questionExpireA).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

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
          {isExpired ? (
            <p
              className="mb-1 text-micro uppercase tracking-wide text-zinc-500"
              data-testid="question-expiree"
            >
              Question expirée à {expireLabel} — l'agent a repris sur une hypothèse
            </p>
          ) : (
            <p className="mb-1 text-micro uppercase tracking-wide text-amber-500">
              L'agent attend votre réponse
            </p>
          )}
          <p
            className={`rounded-sm border px-2 py-1.5 text-xs ${
              isExpired
                ? "border-zinc-700 bg-zinc-800/40 text-zinc-400"
                : "border-amber-900/60 bg-amber-950/30 text-amber-100"
            }`}
          >
            {pendingQuestion}
          </p>
          {!isExpired && (
            <div className="mb-2">
              <CompteARebours expireA={questionExpireA} />
            </div>
          )}
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
              className="min-w-0 flex-1 rounded-sm border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-100 outline-hidden focus:border-zinc-500"
            />
            <button
              type="button"
              onClick={envoyerReponse}
              className="rounded-sm bg-amber-700 px-2 py-1 text-xs text-amber-50 transition-colors hover:bg-amber-600"
            >
              Répondre
            </button>
          </div>
        </div>
      ) : null}

      {answerAck === "deposited" && (
        <p
          className="mb-2 text-micro text-zinc-500"
          data-testid="answer-ack-deposited"
        >
          Votre réponse a été déposée pour le tour suivant.
        </p>
      )}

      {answerAck === "transmitted" && (
        <p
          className="mb-2 text-micro text-zinc-500"
          data-testid="answer-ack-transmitted"
        >
          Réponse transmise à l'agent.
        </p>
      )}

      {/* L'arrêt est une sortie, pas une annulation : le run commite ce qu'il
          a déjà produit, parce que le ticket suivant dépend d'un arbre propre
          (ADR-018). */}
      <button
        type="button"
        onClick={onStop}
        title="Le run commitera ce qu'il a déjà produit"
        className="mb-3 rounded-sm border border-red-900/70 px-2 py-0.5 text-micro text-red-400 transition-colors hover:border-red-700 hover:text-red-300"
      >
        Arrêter le run
      </button>

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
          className="min-w-0 flex-1 rounded-sm border border-zinc-800 bg-zinc-950 px-2 py-1 text-xs text-zinc-200 outline-hidden placeholder:text-zinc-600 focus:border-zinc-600"
        />
        <button
          type="button"
          onClick={envoyerConsigne}
          className="rounded-sm border border-zinc-700 px-2 py-1 text-xs text-zinc-300 transition-colors hover:border-zinc-500 hover:text-zinc-100"
        >
          Envoyer
        </button>
      </div>
    </div>
  );
}
