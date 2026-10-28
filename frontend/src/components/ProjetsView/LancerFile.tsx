import { useState } from "react";
import Button from "../../design/ui/Button";
import { api } from "../../lib/api";
import type { ProjectOverview } from "../../types/api";
import { BULLE } from "./BoutonServices";
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

/** Ce que le bouton propose : lancer une file, la compléter, ou un seul ticket. */
type Mode = "file" | "ajout" | "suivant";

const QUESTION: Record<Mode, (n: number) => string> = {
  file: (n) => `Lancer ${n} tickets ?`,
  ajout: (n) => `Ajouter ${n} tickets à la file en cours ?`,
  suivant: () => "Lancer le prochain ticket à faire, seul ?",
};

const LIBELLE: Record<Mode, (n: number) => string> = {
  file: (n) => `File (${n})`,
  ajout: (n) => `Ajouter à la file (${n})`,
  suivant: () => "Ticket suivant",
};

/**
 * Lance la file des tickets « à faire » d'un projet depuis sa carte — ticket-412.
 *
 * Quand une file tourne déjà sur le projet, le bouton y ajoute les tickets au
 * lieu d'être grisé (ticket-557). Un projet à worktree ne tourne qu'un ticket à
 * la fois (ADR-056) : le bouton y lance le prochain ticket seul, au lieu d'une
 * file que le backend refuserait (ticket-633). La confirmation et les messages
 * s'ouvrent en bulle au-dessus du bouton, sans pousser la carte. Tout clic ici
 * s'arrête : la carte n'est pas sélectionnée.
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
  const mode: Mode = projet.worktree
    ? "suivant"
    : projet.run_actif && fileEnCours !== null
      ? "ajout"
      : "file";
  const ajout = mode === "ajout";
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
      if (mode === "suivant") {
        const [premier] = ids;
        if (premier) {
          await api.orchestrator.run({
            project_id: projet.id,
            mode: "single",
            ticket_id: premier,
          });
          setResultat(`${premier} lancé`);
        }
      } else if (ajout && fileEnCours) {
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
      // La bulle de confirmation se referme : l'erreur prend sa place.
      setConfirmation(false);
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
      className="relative shrink-0"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <Button
        taille="compact"
        disabled={bloque || enCours}
        title={bloque ? "Un run est en cours" : undefined}
        onClick={() => setConfirmation(true)}
      >
        {LIBELLE[mode](n)}
      </Button>
      {confirmation && (
        <div className={`${BULLE} flex flex-col items-end gap-1.5`}>
          <span className="text-zinc-300">{QUESTION[mode](n)}</span>
          <span className="flex gap-1.5">
            <Button
              taille="compact"
              variante="discret"
              disabled={enCours}
              onClick={() => setConfirmation(false)}
            >
              Annuler
            </Button>
            <Button
              taille="compact"
              disabled={enCours}
              onClick={() => void lancer()}
            >
              {ajout ? "Ajouter" : "Lancer"}
            </Button>
          </span>
        </div>
      )}
      {!confirmation && resultat && (
        <span role="status" className={`${BULLE} text-zinc-400`}>
          {resultat}
        </span>
      )}
      {!confirmation && echec && (
        <span role="alert" className={`${BULLE} text-red-400`}>
          {echec}
        </span>
      )}
    </div>
  );
}
