import { useState } from "react";
import { API_ORIGIN } from "../../lib/config";
import { withTokenQuery } from "../../lib/auth";
import type { ProjectOverview } from "../../types/api";

interface IconeDuProjetProps {
  projet: Pick<ProjectOverview, "id" | "name" | "icon">;
  /** `carte` pour la vue Projets, `tuile` pour les projets arrêtés (ticket-721). */
  taille?: "carte" | "tuile";
}

const DIMENSION = { carte: "size-10 text-base", tuile: "size-7 text-sm" } as const;

/** Carré d'icône : l'icône du projet, ou à défaut son initiale. Partagé par la vue Projets et « En cours ». */
export default function IconeDuProjet({ projet, taille = "carte" }: IconeDuProjetProps) {
  const [cassee, setCassee] = useState(false);
  const dimension = DIMENSION[taille];
  if (projet.icon && !cassee) {
    const url = `${API_ORIGIN}/api/v1/projects/${projet.id}/icon`;
    return (
      <img
        src={withTokenQuery(url)}
        alt=""
        onError={() => setCassee(true)}
        className={`${dimension} shrink-0 rounded-sm object-contain`}
      />
    );
  }
  return (
    <span
      data-testid="icone-initiale"
      aria-hidden="true"
      className={`flex ${dimension} shrink-0 items-center justify-center rounded-sm bg-zinc-800 font-medium text-zinc-300`}
    >
      {projet.name.trim().charAt(0).toUpperCase() || "?"}
    </span>
  );
}
