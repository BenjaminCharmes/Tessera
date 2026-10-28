import { useState, type KeyboardEvent } from "react";
import { IconExternal } from "../../design/icons";
import { API_ORIGIN } from "../../lib/config";
import { withTokenQuery } from "../../lib/auth";
import { lienDuDepot } from "../../lib/lienDuDepot";
import type { ProjectOverview } from "../../types/api";
import { dateExacte, ilYa } from "./dates";
import BoutonMiseEnLigne from "../MiseEnLigne/BoutonMiseEnLigne";
import BoutonServices from "./BoutonServices";
import LancerFile from "./LancerFile";
import MenuCategorie from "./MenuCategorie";

interface ProjetCarteProps {
  projet: ProjectOverview;
  /** C'est le projet actif du cockpit. */
  actif: boolean;
  /** Un run de ce projet attend une réponse (ticket-186). */
  enAttente?: boolean;
  categories: string[];
  onSelect: () => void;
  onChangerCategorie: (categorie: string) => void;
  /** Les services du projet viennent d'être lancés ou arrêtés. */
  onServicesChange: () => void;
  /** La file du projet vient de partir : la vue d'ensemble est à relire. */
  onFileLancee: () => void;
  /** Le run de la file qui tourne sur ce projet, s'il y en a une (ticket-557). */
  fileEnCours?: string | null;
  /** Les tickets que la file en cours doit encore traiter (ticket-622). */
  dejaEnFile?: readonly string[];
}

/** L'état de l'app du projet, pour la carte ; `undefined` sans rien à lancer. */
function etatServices(projet: ProjectOverview): string | undefined {
  if (projet.services_en_cours) return "en-cours";
  return projet.services_declares ? "a-l-arret" : undefined;
}

/** Carré d'icône : l'icône du projet, ou à défaut son initiale. */
function Icone({ projet }: { projet: ProjectOverview }) {
  const [cassee, setCassee] = useState(false);
  if (projet.icon && !cassee) {
    const url = `${API_ORIGIN}/api/v1/projects/${projet.id}/icon`;
    return (
      <img
        src={withTokenQuery(url)}
        alt=""
        onError={() => setCassee(true)}
        className="size-10 shrink-0 rounded-sm object-contain"
      />
    );
  }
  return (
    <span
      data-testid="icone-initiale"
      className="flex size-10 shrink-0 items-center justify-center rounded-sm bg-zinc-800 text-base font-medium text-zinc-300"
    >
      {projet.name.trim().charAt(0).toUpperCase() || "?"}
    </span>
  );
}

function Compteurs({ projet }: { projet: ProjectOverview }) {
  const t = projet.tickets;
  const lignes: { libelle: string; nombre: number; couleur: string }[] = [
    { libelle: "À faire", nombre: t.todo, couleur: "text-zinc-400" },
    { libelle: "En cours", nombre: t.in_progress, couleur: "text-blue-400" },
    { libelle: "Bloqués", nombre: t.blocked, couleur: "text-red-400" },
    { libelle: "Faits", nombre: t.done, couleur: "text-green-400" },
  ];
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-0.5 text-micro">
      {lignes.map((l) => (
        <li key={l.libelle} className={l.couleur}>
          {l.libelle} <span className="font-medium">{l.nombre}</span>
        </li>
      ))}
    </ul>
  );
}

function Dates({ projet }: { projet: ProjectOverview }) {
  const activite = ilYa(projet.last_activity);
  return (
    <p className="flex flex-wrap gap-x-3 text-micro text-zinc-500">
      <span title={dateExacte(projet.created_at)}>
        Créé {ilYa(projet.created_at)}
      </span>
      {activite && (
        <span title={dateExacte(projet.last_activity)}>
          Activité {activite}
        </span>
      )}
    </p>
  );
}

function LienDepot({ projet }: { projet: ProjectOverview }) {
  const lien = lienDuDepot(projet.github_remote);
  if (!lien) return null;
  return (
    <a
      href={lien}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Ouvrir le dépôt de ${projet.name}`}
      onClick={(e) => e.stopPropagation()}
      className="inline-flex max-w-full items-center gap-1 text-micro text-zinc-500 hover:text-zinc-200"
    >
      <IconExternal size={12} />
      <span className="truncate">{lien.replace(/^https?:\/\//, "")}</span>
    </a>
  );
}

/**
 * Une carte de la vue Projets — ticket-399.
 *
 * La carte est une région focalisable plutôt qu'un `<button>` : elle porte un
 * lien et un menu, et deux cibles imbriquées se disputeraient le clic
 * (ticket-123). Entrée ne sélectionne que si la carte elle-même a le focus.
 */
export default function ProjetCarte({
  projet,
  actif,
  enAttente = false,
  categories,
  onSelect,
  onChangerCategorie,
  onServicesChange,
  onFileLancee,
  fileEnCours = null,
  dejaEnFile = [],
}: ProjetCarteProps) {
  function surClavier(e: KeyboardEvent<HTMLElement>) {
    if (e.key === "Enter" && e.target === e.currentTarget) onSelect();
  }

  return (
    <article
      tabIndex={0}
      aria-label={projet.name}
      aria-current={actif ? "true" : undefined}
      onClick={onSelect}
      onKeyDown={surClavier}
      data-services={etatServices(projet)}
      className={`flex cursor-pointer flex-col gap-2 rounded-sm border bg-zinc-900 p-3 outline-hidden transition-colors hover:bg-zinc-800/60 focus-visible:border-zinc-500 ${
        // L'app qui tourne se voit de loin : bordure bleue (ADR-026 : `blue`
        // pour l'activité). Lançable mais à l'arrêt : bordure plus claire que
        // celle d'un projet sans rien à lancer.
        projet.services_en_cours
          ? "border-blue-500/60"
          : projet.services_declares
            ? "border-zinc-700"
            : "border-zinc-800"
      } ${
        // Le projet actif seul reçoit la barre violette, plus épaisse
        // (ADR-026 : identité).
        actif ? "border-l-2 border-l-violet-500" : ""
      }`}
    >
      <div className="flex items-start gap-3">
        <Icone projet={projet} />
        <div className="min-w-0 flex-1">
          <h3 className="flex items-center gap-2 truncate text-sm font-medium text-zinc-100">
            {projet.name}
            {projet.run_actif && (
              <span
                role="status"
                aria-label="Un run est en cours"
                title="Un run est en cours"
                className="size-1.5 shrink-0 animate-pulse rounded-full bg-blue-400"
              />
            )}
            {/* Ambre : une attente, au sens d'ADR-026 (ticket-186). */}
            {enAttente && (
              <span
                role="status"
                aria-label="Un agent attend une réponse"
                title="Un agent attend une réponse"
                className="size-1.5 shrink-0 rounded-full bg-amber-400"
              />
            )}
          </h3>
          <p className="truncate text-micro text-zinc-500">
            {projet.id} · {projet.category?.trim() || "Sans catégorie"}
          </p>
        </div>
        <MenuCategorie
          projet={projet.name}
          actuelle={projet.category?.trim() || null}
          categories={categories}
          onChoisir={onChangerCategorie}
        />
      </div>
      {projet.description && (
        <p className="line-clamp-3 text-xs text-zinc-400">
          {projet.description}
        </p>
      )}
      <LienDepot projet={projet} />
      {/* Les cartes d'une rangée ont la même hauteur : le pied est poussé en
          bas pour que dates et compteurs s'alignent d'une carte à l'autre,
          quelle que soit la longueur de la description. */}
      <div data-testid="pied-de-carte" className="mt-auto flex flex-col gap-2">
        <Dates projet={projet} />
        <Compteurs projet={projet} />
        {/* Une seule rangée d'actions, alignée à droite, qui se replie
            proprement : File, Mettre en ligne, Lancer (ticket-557). */}
        <div
          data-testid="actions-de-carte"
          className="flex flex-wrap items-start justify-end gap-1.5"
        >
          <LancerFile
            projet={projet}
            fileEnCours={fileEnCours}
            dejaEnFile={dejaEnFile}
            onLancee={onFileLancee}
          />
          <BoutonMiseEnLigne projet={projet} />
          <BoutonServices projet={projet} onChange={onServicesChange} />
        </div>
      </div>
    </article>
  );
}
