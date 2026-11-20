import { useState } from "react";
import { useImageAuthentifiee } from "../../hooks/useImageAuthentifiee";
import type { ProjectOverview } from "../../types/api";

interface IconeDuProjetProps {
  projet: Pick<ProjectOverview, "id" | "name" | "icon">;
  /** `carte` pour la vue Projets, `tuile` pour les projets arrêtés (ticket-721), `titre` à côté d'un nom de salle (ticket-726). */
  taille?: "carte" | "tuile" | "titre";
}

const DIMENSION = { carte: "size-10 text-base", tuile: "size-7 text-sm", titre: "size-5 text-micro" } as const;

/** Carré d'icône : l'icône du projet, ou à défaut son initiale. Partagé par la vue Projets et « En cours ». */
export default function IconeDuProjet({ projet, taille = "carte" }: IconeDuProjetProps) {
  const [cassee, setCassee] = useState(false);
  const dimension = DIMENSION[taille];
  const image = useImageAuthentifiee(projet.icon ? `/projects/${encodeURIComponent(projet.id)}/icon` : null);
  if (image.src !== null && !cassee && !image.echec) {
    return (
      <img
        src={image.src}
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
