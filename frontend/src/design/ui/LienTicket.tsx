import { useState } from "react";
import { useOuvrirTicket } from "../../hooks/useOuvrirTicket";

interface LienTicketProps {
  /** Le projet du ticket ; null quand on ne le connaît pas : texte brut. */
  projectId: string | null;
  ticketId: string;
  className?: string;
}

/**
 * Un numéro de ticket qui ouvre le ticket — ticket-460.
 *
 * C'est un `<button>` stylé en lien : il se prend au clavier et Entrée
 * l'active sans code. Le soulignement vient du survol, jamais d'une couleur
 * de texte d'identité (ADR-026). Le clic et le clavier ne remontent pas :
 * le lien vit dans des cartes et des lignes qui sont elles-mêmes
 * interactives.
 */
export default function LienTicket({
  projectId,
  ticketId,
  className = "",
}: LienTicketProps) {
  const ouvrir = useOuvrirTicket();
  const [introuvable, setIntrouvable] = useState(false);

  if (projectId === null) return <>{ticketId}</>;

  async function ouvrirLeTicket() {
    if (projectId === null) return;
    setIntrouvable((await ouvrir(projectId, ticketId)) === "introuvable");
  }

  return (
    <>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          void ouvrirLeTicket();
        }}
        onKeyDown={(e) => e.stopPropagation()}
        className={`rounded-sm hover:underline focus-visible:underline focus-visible:outline focus-visible:outline-1 focus-visible:outline-zinc-400 ${className}`}
      >
        {ticketId}
      </button>
      {introuvable ? (
        <span role="status" className="ml-2 text-micro text-amber-300">
          Ticket introuvable
        </span>
      ) : null}
    </>
  );
}
