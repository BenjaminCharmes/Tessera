/**
 * Jeton de session côté client (ticket-877).
 *
 * Le backend exige `Authorization: Bearer <jeton>` sur toute requête HTTP et
 * `?token=<jeton>` sur toute WebSocket — un navigateur ne peut pas poser
 * d'en-tête sur `new WebSocket(url)`. Le jeton n'est jamais inscrit dans le
 * code servi par Vite : il vient de la mémoire, de `sessionStorage` (perdu à la fermeture de l'onglet), du
 * fragment `#jeton=<t>` de l'URL, ou de la commande Tauri `jeton_de_session`.
 * Il se lit à chaque appel plutôt qu'au chargement du module.
 */
import { invoke } from "@tauri-apps/api/core";

const CLE_STOCKAGE = "tessera.jeton";
const PARAMETRE_FRAGMENT = "jeton";

let enMemoire = "";
let lectureTauri: Promise<string> | null = null;

function ecrireStockage(jeton: string): void {
  try {
    window.sessionStorage.setItem(CLE_STOCKAGE, jeton);
  } catch {
    // Stockage refusé : le jeton reste en mémoire pour cette session.
  }
}

/** Efface un jeton hérité de `localStorage`, partagé par toute page de la même origine. */
function effacerHeritage(): void {
  try {
    window.localStorage.removeItem(CLE_STOCKAGE);
  } catch {
    // Stockage inaccessible : rien à effacer.
  }
}

/** Lit `sessionStorage`, propre à l'onglet, après avoir effacé l'ancien `localStorage`. */
function lireStockage(): string {
  effacerHeritage();
  try {
    return window.sessionStorage.getItem(CLE_STOCKAGE) ?? "";
  } catch {
    return "";
  }
}

/** Prend le jeton du fragment, le range en `sessionStorage` et efface le fragment. */
function lireFragment(): string {
  const parametres = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const jeton = parametres.get(PARAMETRE_FRAGMENT) ?? "";
  if (!jeton) return "";
  ecrireStockage(jeton);
  const { pathname, search } = window.location;
  window.history.replaceState(window.history.state, "", `${pathname}${search}`);
  return jeton;
}

/** Jeton déjà connu, sans attente : mémoire, stockage, puis fragment. */
export function jetonEnCache(): string {
  return enMemoire || lireStockage() || lireFragment();
}

function dansTauri(): boolean {
  return "__TAURI_INTERNALS__" in window;
}

async function lireViaTauri(): Promise<string> {
  try {
    return await invoke<string>("jeton_de_session");
  } catch {
    // Fichier absent ou illisible : le bandeau demandera la saisie au premier 401.
    return "";
  }
}

/**
 * Jeton de la session, en allant le chercher dans Tauri si besoin. La commande
 * n'est appelée qu'une fois : son résultat est mis en cache.
 */
export async function jetonDeSession(): Promise<string> {
  const connu = jetonEnCache();
  if (connu || !dansTauri()) return connu;
  lectureTauri ??= lireViaTauri();
  const jeton = await lectureTauri;
  if (jeton) enMemoire = jeton;
  else lectureTauri = null;
  return jeton;
}

/** Jeton saisi à la main : rangé en `sessionStorage`, servi à la requête suivante. */
export function saisirJeton(jeton: string): void {
  const propre = jeton.trim();
  enMemoire = propre;
  if (propre) ecrireStockage(propre);
}

/** Oublie le jeton en mémoire et dans les stockages (jeton périmé, tests). */
export function oublierJeton(): void {
  enMemoire = "";
  lectureTauri = null;
  try {
    window.localStorage.removeItem(CLE_STOCKAGE);
    window.sessionStorage.removeItem(CLE_STOCKAGE);
  } catch {
    // Rien à retirer si le stockage est inaccessible.
  }
}

/** `init` enrichi du Bearer si un jeton est connu, `init` inchangé sinon. */
export function authorized(init?: RequestInit): RequestInit | undefined {
  const token = jetonEnCache();
  if (!token) return init;
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return { ...init, headers };
}

/** `url` avec `token=` ajouté à la query si un jeton est connu. */
export function withTokenQuery(url: string): string {
  const token = jetonEnCache();
  if (!token) return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}token=${encodeURIComponent(token)}`;
}
