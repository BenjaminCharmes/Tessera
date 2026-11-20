import { useState } from "react";
import Button from "../../design/ui/Button";
import { api } from "../../lib/api";
import { formatUsd } from "../../lib/format";
import { plafondDeRevue, ticketEnCours } from "../../lib/plafondDeRevue";
import type { ProjectOverview } from "../../types/api";
import { BULLE } from "./BoutonServices";

interface RevueProjetBoutonProps {
  projet: ProjectOverview;
  /** Appelé une fois la revue partie : la vue relit la vue d'ensemble. */
  onLancee: () => void;
}

/** Où en est le bouton : rien, une estimation en cours, une question, un lancement. */
type Etape =
  | { nom: "repos" }
  | { nom: "estimation" }
  | { nom: "confirmation"; plafond: number }
  | { nom: "lancement"; plafond: number };

/** Le projet est occupé : le message dit par quoi, et le bouton reste grisé. */
interface Occupe {
  ticket: string | null;
}

function messageDOccupation({ ticket }: Occupe): string {
  return ticket
    ? `Un run est déjà en cours sur ce projet : ${ticket}.`
    : "Un run est déjà en cours sur ce projet.";
}

/**
 * Lance la revue d'un projet depuis sa carte — ticket-865, ADR-080.
 *
 * Le coût est borné par le plafond, qu'on lit avant de demander confirmation :
 * annuler n'envoie aucune requête de lancement. Une fois partie, la revue est un
 * run comme les autres, qui s'observe dans le fil (ADR-041) : aucun écran propre.
 * Un 409 grise le bouton pour de bon, jusqu'à ce que la vue relise le projet.
 */
export default function RevueProjetBouton({
  projet,
  onLancee,
}: RevueProjetBoutonProps) {
  const [etape, setEtape] = useState<Etape>({ nom: "repos" });
  const [occupe, setOccupe] = useState<Occupe | null>(null);
  const [echec, setEchec] = useState<string | null>(null);

  async function estimer() {
    setEchec(null);
    setEtape({ nom: "estimation" });
    try {
      const { run_max_budget_usd } = await api.orchestrator.limits();
      setEtape({ nom: "confirmation", plafond: plafondDeRevue(run_max_budget_usd) });
    } catch (e) {
      setEtape({ nom: "repos" });
      setEchec(e instanceof Error ? e.message : "Estimation impossible.");
    }
  }

  async function lancer(plafond: number) {
    setEtape({ nom: "lancement", plafond });
    try {
      await api.orchestrator.run({ project_id: projet.id, mode: "revue" });
      setEtape({ nom: "repos" });
      onLancee();
    } catch (e) {
      const texte = e instanceof Error ? e.message : "";
      setEtape({ nom: "repos" });
      if (texte.startsWith("API 409")) setOccupe({ ticket: ticketEnCours(texte) });
      else setEchec(texte || "Lancement impossible.");
    }
  }

  const bloque = occupe !== null || projet.run_actif;
  const ouverte = etape.nom === "confirmation" || etape.nom === "lancement";
  return (
    <div
      className="relative shrink-0"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <Button
        taille="compact"
        disabled={bloque || etape.nom !== "repos"}
        title={bloque ? "Un run est en cours" : undefined}
        onClick={() => void estimer()}
      >
        Revue du projet
      </Button>
      {etape.nom === "confirmation" || etape.nom === "lancement" ? (
        <div className={`${BULLE} flex flex-col items-end gap-1.5`}>
          <span className="text-zinc-300">
            Coût estimé : jusqu'à {formatUsd(etape.plafond)}. Plafond de la revue :{" "}
            {formatUsd(etape.plafond)}.
          </span>
          <span className="flex gap-1.5">
            <Button
              taille="compact"
              variante="discret"
              disabled={etape.nom === "lancement"}
              onClick={() => setEtape({ nom: "repos" })}
            >
              Annuler
            </Button>
            <Button
              taille="compact"
              disabled={etape.nom === "lancement"}
              onClick={() => void lancer(etape.plafond)}
            >
              Lancer la revue
            </Button>
          </span>
        </div>
      ) : null}
      {!ouverte && occupe && (
        <span role="alert" className={`${BULLE} text-amber-400`}>
          {messageDOccupation(occupe)}
        </span>
      )}
      {!ouverte && !occupe && echec && (
        <span role="alert" className={`${BULLE} text-red-400`}>
          {echec}
        </span>
      )}
    </div>
  );
}
