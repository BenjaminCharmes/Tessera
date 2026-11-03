import { useState } from "react";
import { signalerATessera } from "../../lib/api";
import Modale from "../../design/ui/Modale";
import type { Project, SignalementNature } from "../../types/api";

interface SignalementModalProps {
  /** Le projet depuis lequel on signale : il part avec le signalement. */
  project: Project;
  onClose: () => void;
}

const NATURES: { value: SignalementNature; label: string }[] = [
  { value: "bug", label: "Bug" },
  { value: "idee", label: "Idée" },
];

const CHAMP =
  "w-full bg-zinc-800 border border-zinc-600 rounded-sm px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-hidden focus:border-zinc-400";

/**
 * Signale un défaut ou une idée sur Tessera depuis le projet ouvert
 * (ticket-408). Le ticket naît dans ide-core ; la modale n'en montre que l'id.
 */
export default function SignalementModal({
  project,
  onClose,
}: SignalementModalProps) {
  const [nature, setNature] = useState<SignalementNature>("bug");
  const [titre, setTitre] = useState("");
  const [description, setDescription] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const [ticketId, setTicketId] = useState<string | null>(null);

  const incomplet = !titre.trim() || !description.trim();

  async function envoyer(e: React.FormEvent) {
    e.preventDefault();
    if (incomplet || envoi) return;
    setErreur(null);
    setEnvoi(true);
    try {
      const ticket = await signalerATessera({
        projet: project.id,
        nature,
        titre: titre.trim(),
        description: description.trim(),
      });
      setTicketId(ticket.id);
    } catch (err: unknown) {
      // Le formulaire reste tel quel : on ne perd pas ce qui a été saisi.
      setErreur(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <Modale onFermer={onClose} aria-label="Signaler à Tessera">
      <div className="w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-900 p-6 shadow-xl">
        <h2 className="mb-4 text-base font-semibold text-zinc-100">
          Signaler à Tessera
        </h2>
        {ticketId ? (
          <div>
            <p className="mb-4 text-sm text-green-400" role="status">
              Signalé : {ticketId}
            </p>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="rounded-sm bg-zinc-700 px-4 py-2 text-sm text-white transition-colors hover:bg-zinc-600"
              >
                Fermer
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={envoyer} noValidate>
            <fieldset className="mb-4 flex gap-4" disabled={envoi}>
              <legend className="mb-1 text-xs text-zinc-400">Nature</legend>
              {NATURES.map((n) => (
                <label
                  key={n.value}
                  className="flex items-center gap-1.5 text-sm text-zinc-200"
                >
                  <input
                    type="radio"
                    name="signalement-nature"
                    value={n.value}
                    checked={nature === n.value}
                    onChange={() => setNature(n.value)}
                  />
                  {n.label}
                </label>
              ))}
            </fieldset>

            <div className="mb-4">
              <label
                htmlFor="signalement-titre"
                className="mb-1 block text-xs text-zinc-400"
              >
                Titre
              </label>
              <input
                id="signalement-titre"
                type="text"
                value={titre}
                onChange={(e) => setTitre(e.target.value)}
                maxLength={100}
                className={CHAMP}
                disabled={envoi}
                autoFocus
              />
            </div>

            <div className="mb-5">
              <label
                htmlFor="signalement-description"
                className="mb-1 block text-xs text-zinc-400"
              >
                Description
              </label>
              <textarea
                id="signalement-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={5}
                className={`${CHAMP} resize-none`}
                disabled={envoi}
              />
            </div>

            {erreur && (
              <p className="mb-4 text-xs text-red-400" role="alert">
                Envoi impossible : {erreur}
              </p>
            )}

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={envoi}
                className="px-4 py-2 text-sm text-zinc-400 transition-colors hover:text-zinc-200 disabled:opacity-50"
              >
                Annuler
              </button>
              <button
                type="submit"
                disabled={incomplet || envoi}
                className="rounded-sm bg-zinc-700 px-4 py-2 text-sm text-white transition-colors hover:bg-zinc-600 disabled:opacity-50"
              >
                Envoyer
              </button>
            </div>
          </form>
        )}
      </div>
    </Modale>
  );
}
