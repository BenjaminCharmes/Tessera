import { useState } from "react";
import type { ReactNode } from "react";
import { libelleDeLAttente, resteAvant } from "../AgentPanel/attente";
import Button from "../../design/ui/Button";
import StatusPill from "../../design/ui/StatusPill";
import { LIBELLE_SANTE } from "../../lib/santeAgent";
import type { ContenuAToi, QuestionAToi } from "../../lib/bureau/aToi";

export interface ReglageSon {
  actif: boolean;
  regler: (actif: boolean) => void;
}

interface ColonneAToiProps {
  contenu: ContenuAToi;
  /** L'horloge du Bureau : le compte à rebours n'ouvre pas de minuteur. */
  maintenant: number;
  onAnswer: (runId: string, texte: string) => void;
  son: ReglageSon;
}

function Groupe({ titre, enfants }: { titre: string; enfants: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <h4 className="text-micro uppercase tracking-wide text-zinc-500">{titre}</h4>
      {enfants}
    </div>
  );
}

interface CarteQuestionProps {
  question: QuestionAToi;
  maintenant: number;
  onAnswer: (runId: string, texte: string) => void;
}

/**
 * Une question d'agent. Pas de « Laisser l'agent choisir » : le canal n'a que
 * `answer`, `interject` et `stop`, et l'agent choisit seul à l'échéance (ADR-025).
 */
function CarteQuestion({ question, maintenant, onAnswer }: CarteQuestionProps) {
  const [reponse, setReponse] = useState("");
  const { runId } = question;
  const attente = libelleDeLAttente(resteAvant(question.expireA, maintenant));

  function envoyer() {
    const texte = reponse.trim();
    if (!texte || runId === null) return;
    onAnswer(runId, texte);
    setReponse("");
  }

  return (
    <li className="rounded-md border border-amber-900/60 bg-amber-950/30 p-2">
      <p className="text-micro text-zinc-400">{question.projet}</p>
      <p className="text-xs text-amber-100">{question.question}</p>
      {attente && (
        <p className="mt-1 text-micro text-amber-600" data-testid="compte-a-rebours">
          {attente}
        </p>
      )}
      {runId !== null && (
        <div className="mt-1.5 flex gap-1.5">
          <input
            aria-label={`Réponse pour ${question.projet}`}
            value={reponse}
            onChange={(e) => setReponse(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && envoyer()}
            className="min-w-0 flex-1 rounded-sm border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-100 outline-hidden focus:border-zinc-500"
          />
          <Button taille="compact" onClick={envoyer} aria-label={`Répondre à ${question.projet}`}>
            Répondre
          </Button>
        </div>
      )}
    </li>
  );
}

/** Le bouton du Bureau : un second interrupteur sur le réglage « Son » de la question (ticket-554). */
function InterrupteurSon({ son }: { son: ReglageSon }) {
  return (
    <Button
      taille="compact"
      aria-pressed={son.actif}
      aria-label="Son des questions"
      onClick={() => son.regler(!son.actif)}
    >
      {son.actif ? "Son activé" : "Son coupé"}
    </Button>
  );
}

/** Ce qui attend une action humaine : questions, agents figés, PR à relire. */
export default function ColonneAToi({ contenu, maintenant, onAnswer, son }: ColonneAToiProps) {
  const { questions, figes, prs } = contenu;
  const vide = questions.length + figes.length + prs.length === 0;

  return (
    <aside
      aria-label="À toi"
      className="flex flex-col gap-3 rounded-lg border border-zinc-800 bg-zinc-900 p-3"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-corps font-semibold text-zinc-200">À toi</h3>
        <InterrupteurSon son={son} />
      </div>
      {vide && <p className="text-micro text-zinc-500">Rien n'attend ta réponse.</p>}
      {questions.length > 0 && (
        <Groupe
          titre="Questions"
          enfants={
            <ul className="flex flex-col gap-1.5">
              {questions.map((q) => (
                <CarteQuestion key={q.projet} question={q} maintenant={maintenant} onAnswer={onAnswer} />
              ))}
            </ul>
          }
        />
      )}
      {figes.length > 0 && (
        <Groupe
          titre="Figés"
          enfants={
            <ul className="flex flex-col gap-1.5">
              {figes.map((projet) => (
                <li key={projet} className="flex items-center justify-between gap-2 text-xs text-zinc-300">
                  {projet}
                  <StatusPill etat="echec" libelle={LIBELLE_SANTE.blocage_suspecte} />
                </li>
              ))}
            </ul>
          }
        />
      )}
      {prs.length > 0 && (
        <Groupe
          titre="PR à relire"
          enfants={
            <ul className="flex flex-col gap-1.5">
              {prs.map(({ projet, pr }) => (
                <li key={projet} className="flex items-center justify-between gap-2 text-xs text-zinc-300">
                  {projet}
                  <StatusPill etat="attention" libelle={`PR #${pr}`} titre="Conflit résolu : à relire avant de merger" />
                </li>
              ))}
            </ul>
          }
        />
      )}
    </aside>
  );
}
