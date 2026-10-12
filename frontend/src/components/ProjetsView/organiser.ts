import type { ProjectOverview } from "../../types/api";

/**
 * Chercher, filtrer et trier les projets de la vue d'ensemble — ticket-399.
 *
 * Tout est pur : la vue ne fait que brancher ces fonctions sur son état, et
 * chaque règle se vérifie sans rendre un composant.
 */
export type TriDesProjets = "nom" | "activite" | "creation";

export const TRIS: { valeur: TriDesProjets; libelle: string }[] = [
  { valeur: "nom", libelle: "Nom" },
  { valeur: "activite", libelle: "Activité récente" },
  { valeur: "creation", libelle: "Création récente" },
];

/** Valeur du filtre de catégorie pour les projets qui n'en déclarent aucune. */
export const SANS_CATEGORIE = "\u0000sans-categorie";

export interface FiltresProjets {
  recherche: string;
  /** `null` : toutes les catégories ; sinon un nom, ou `SANS_CATEGORIE`. */
  categorie: string | null;
  tri: TriDesProjets;
}

export const FILTRES_PAR_DEFAUT: FiltresProjets = {
  recherche: "",
  categorie: null,
  tri: "nom",
};

/** Minuscules sans accents : « Deminéur » et « demineur » se valent. */
export function normaliser(texte: string): string {
  return texte.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

export function categorieDe(projet: ProjectOverview): string {
  return projet.category?.trim() || SANS_CATEGORIE;
}

function correspond(projet: ProjectOverview, requete: string): boolean {
  if (requete === "") return true;
  const champs = [projet.name, projet.id, projet.description];
  return champs.some((c) => normaliser(c).includes(requete));
}

export function filtrerProjets(
  projets: ProjectOverview[],
  filtres: FiltresProjets,
): ProjectOverview[] {
  const requete = normaliser(filtres.recherche.trim());
  return projets.filter(
    (p) =>
      correspond(p, requete) &&
      (filtres.categorie === null || categorieDe(p) === filtres.categorie),
  );
}

/** Date en millisecondes ; une date absente ou illisible vaut « la plus ancienne ». */
function horodatage(iso: string | null): number {
  const t = iso ? Date.parse(iso) : Number.NaN;
  return Number.isNaN(t) ? Number.NEGATIVE_INFINITY : t;
}

function parDateDecroissante(a: string | null, b: string | null): number {
  const [ta, tb] = [horodatage(a), horodatage(b)];
  return ta === tb ? 0 : ta > tb ? -1 : 1;
}

function parNom(a: ProjectOverview, b: ProjectOverview): number {
  return a.name.localeCompare(b.name, "fr", { sensitivity: "base" });
}

export function trierProjets(
  projets: ProjectOverview[],
  tri: TriDesProjets,
): ProjectOverview[] {
  const comparateurs: Record<
    TriDesProjets,
    (a: ProjectOverview, b: ProjectOverview) => number
  > = {
    nom: parNom,
    activite: (a, b) =>
      parDateDecroissante(a.last_activity, b.last_activity) || parNom(a, b),
    creation: (a, b) =>
      parDateDecroissante(a.created_at, b.created_at) || parNom(a, b),
  };
  return [...projets].sort(comparateurs[tri]);
}

export interface PastilleDeCategorie {
  /** `SANS_CATEGORIE` pour les projets qui n'en déclarent aucune. */
  valeur: string;
  libelle: string;
  nombre: number;
}

/** Une pastille par catégorie, dans l'ordre de la barre latérale : nommées, puis sans. */
export function pastillesDeCategories(
  projets: ProjectOverview[],
): PastilleDeCategorie[] {
  const nombres = new Map<string, number>();
  for (const p of projets) {
    const cle = categorieDe(p);
    nombres.set(cle, (nombres.get(cle) ?? 0) + 1);
  }
  const nommees = [...nombres.keys()]
    .filter((c) => c !== SANS_CATEGORIE)
    .sort((a, b) => a.localeCompare(b, "fr"));
  const cles = nombres.has(SANS_CATEGORIE) ? [...nommees, SANS_CATEGORIE] : nommees;
  return cles.map((valeur) => ({
    valeur,
    libelle: valeur === SANS_CATEGORIE ? "Sans catégorie" : valeur,
    nombre: nombres.get(valeur) ?? 0,
  }));
}

export function filtresActifs(f: FiltresProjets): boolean {
  return f.recherche.trim() !== "" || f.categorie !== null;
}

export function estFiltresProjets(v: unknown): v is FiltresProjets {
  if (typeof v !== "object" || v === null) return false;
  const o = v as Record<string, unknown>;
  return (
    typeof o.recherche === "string" &&
    (o.categorie === null || typeof o.categorie === "string") &&
    TRIS.some((t) => t.valeur === o.tri)
  );
}
