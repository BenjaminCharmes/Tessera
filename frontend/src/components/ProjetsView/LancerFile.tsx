import { useState } from "react";
import Button from "../../design/ui/Button";
import { api } from "../../lib/api";
import type { ProjectOverview } from "../../types/api";
import { idsAFaire } from "./idsAFaire";

interface LancerFileProps {
  projet: ProjectOverview;
  /** Le run de la file qui tourne déjà sur ce projet, s'il y en a une — ticket-557. */
  fileEnCours?: string | null;
  /** Les tickets que cette file doit encore traiter : ni comptés ni proposés de nouveau (ticket-622). */
  dejaEnFile?: readonly string[];
  /** Appelé une fois la file partie ou complétée : la vue relit la vue d'ensemble. */
  onLancee: () => void;
}

function messageDEchec(e: unknown, ajout: boolean): string {
  const texte = e instanceof Error ? e.message : "";
  if (texte.startsWith("API 409")) {
    return ajout
      ? "La file en cours n'accepte plus de tickets."
      : "Un run est déjà en cours sur ce projet.";
  }
  return texte || "Lancement impossible.";
}

function bilan(ajoutes: number): string {
  if (ajoutes === 0) return "Déjà dans la file";
  return `${ajoutes} ajouté${ajoutes > 1 ? "s" : ""}`;
}

/**
 * Lance la file des tickets « à faire » d'un projet depuis sa carte — ticket-412.
 *
 * Quand une file tourne déjà sur le projet, le bouton y ajoute les tickets au
 * lieu d'être grisé (ticket-557). Pendant un run d'un seul ticket, il reste
 * grisé et le dit en clair. La confirmation se fait sur place, sans fenêtre
 * modale. Tout clic ici s'arrête : la carte n'est pas sélectionnée.
 */
export default function LancerFile({
  projet,
  fileEnCours = null,
  dejaEnFile = [],
  onLancee,
}: LancerFileProps) {
  const [confirmation, setConfirmation] = useState(false);
  const [enCours, setEnCours] = useState(false);
  const [echec, setEchec] = useState<string | null>(null);
  const [resultat, setResultat] = useState<string | null>(null);
  const ajout = projet.run_actif && fileEnCours !== null;
  // Le bouton restait « Ajouter à la file (n) » une fois tout ajouté : on croyait
  // que rien n'était parti, et on cliquait en boucle (ticket-622).
  const n = ajout
    ? Math.max(projet.tickets.todo - dejaEnFile.length, 0)
    : projet.tickets.todo;

  async function lancer() {
    setEnCours(true);
    setEchec(null);
    setResultat(null);
    try {
      const { tickets } = await api.tickets.list(projet.id);
      const ids = idsAFaire(tickets).filter(
        (id) => !(ajout && dejaEnFile.includes(id)),
      );
      if (ajout && fileEnCours) {
        const { ajoutes } = await api.orchestrator.append(fileEnCours, ids);
        setResultat(bilan(ajoutes.length));
      } else {
        await api.orchestrator.run({
          project_id: projet.id,
          mode: "queue",
          ticket_ids: ids,
        });
      }
      setConfirmation(false);
      onLancee();
    } catch (e) {
      setEchec(messageDEchec(e, ajout));
    } finally {
      setEnCours(false);
    }
  }

  if (ajout && n <= 0 && projet.tickets.todo > 0) {
    return (
      <span role="status" className="text-micro text-zinc-400">
        Tout est dans la file
      </span>
    );
  }
  if (n <= 0) return null;
  const bloque = projet.run_actif && !ajout;
  return (
    <div
      className="flex flex-wrap items-center justify-end gap-1.5"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      {confirmation ? (
        <>
          <span className="text-micro text-zinc-300">
            {ajout
              ? `Ajouter ${n} tickets à la file en cours ?`
              : `Lancer ${n} tickets ?`}
          </span>
          <Button
            taille="compact"
            disabled={enCours}
            onClick={() => void lancer()}
          >
            {ajout ? "Ajouter" : "Lancer"}
          </Button>
          <Button
            taille="compact"
            variante="discret"
            disabled={enCours}
            onClick={() => setConfirmation(false)}
          >
            Annuler
          </Button>
        </>
      ) : (
        <>
          {bloque && (
            <span className="text-micro text-zinc-500">Run en cours</span>
          )}
          <Button
            taille="compact"
            disabled={bloque}
            title={bloque ? "Un run est en cours" : undefined}
            onClick={() => setConfirmation(true)}
          >
            {ajout ? `Ajouter à la file (${n})` : `File (${n})`}
          </Button>
        </>
      )}
      {resultat && (
        <span role="status" className="text-micro text-zinc-400">
          {resultat}
        </span>
      )}
      {echec && (
        <span role="alert" className="text-micro text-red-400">
          {echec}
        </span>
      )}
    </div>
  );
}
