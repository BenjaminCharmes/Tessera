import { beforeEach, vi } from "vitest";
import { schemaDeLaReponse } from "./openapi";
import { APPELS, appelDe, type Appel } from "./registre";
import { valider } from "./valider";

/** Lève quand `valeur` n'est pas ce que la route de `appel` rend : c'est ce qui fait échouer le test fautif. */
export function exigerConforme(appel: Appel, valeur: unknown): void {
  const ecarts = valider(schemaDeLaReponse(appel.verbe, appel.route), valeur);
  if (ecarts.length > 0) {
    throw new Error(
      `${appel.nom} : la valeur simulée n'est pas la réponse de ${appel.verbe.toUpperCase()} ${appel.route}\n` +
        ecarts.map((e) => `  - ${e}`).join("\n"),
    );
  }
}

interface Simulable {
  mockResolvedValue: (valeur: unknown) => unknown;
  mockResolvedValueOnce: (valeur: unknown) => unknown;
}

const SURVEILLES = new WeakSet<object>();

function surveiller(espion: Simulable, appel: () => Appel | undefined): void {
  if (SURVEILLES.has(espion)) return;
  SURVEILLES.add(espion);
  const unique = espion.mockResolvedValueOnce.bind(espion);
  const durable = espion.mockResolvedValue.bind(espion);
  const verifier = (valeur: unknown): void => {
    const cible = appel();
    if (cible !== undefined) exigerConforme(cible, valeur);
  };
  espion.mockResolvedValue = (valeur) => {
    verifier(valeur);
    return durable(valeur);
  };
  espion.mockResolvedValueOnce = (valeur) => {
    verifier(valeur);
    return unique(valeur);
  };
}

/**
 * Les fonctions du périmètre telles qu'un `vi.mock` les a remplacées, relevées
 * avant chaque test : un mock n'a ni nom de route ni lien avec le client réel.
 */
const MOCKS_VUS = new WeakMap<object, Appel>();

async function releverLesMocks(): Promise<void> {
  for (const appel of APPELS) {
    try {
      const conteneur = (await appel.charger()) as Record<string, unknown> | undefined;
      const fonction = conteneur?.[appel.methode];
      if (typeof fonction === "function" && vi.isMockFunction(fonction)) MOCKS_VUS.set(fonction, appel);
    } catch {
      // La fabrique d'un `vi.mock` n'expose pas ce module : aucun mock à surveiller.
    }
  }
}

type SpyOn = typeof vi.spyOn;
type Mocked = typeof vi.mocked;
const MARQUE = Symbol.for("tessera.contrat.garde");
const MARQUE_MOCKED = Symbol.for("tessera.contrat.garde.mocked");

/**
 * Enveloppe `vi.spyOn` : un espion posé sur une fonction du périmètre refuse
 * toute valeur que `mockResolvedValue` lui donne hors du schéma de sa route.
 * Un `mockImplementation` n'est pas gardé : le contrat le dit dans `perimetre.ts`.
 */
function garderSpyOn(): void {
  const courant: SpyOn & { [MARQUE]?: true } = vi.spyOn;
  if (courant[MARQUE]) return;
  const original: SpyOn = vi.spyOn.bind(vi);
  const garde = ((...args: Parameters<SpyOn>) => {
    const espion = original(...args);
    const appel = appelDe(args[0], String(args[1]));
    if (appel !== undefined) surveiller(espion as unknown as Simulable, () => appel);
    return espion;
  }) as unknown as SpyOn & { [MARQUE]?: true };
  garde[MARQUE] = true;
  vi.spyOn = garde;
}

/**
 * Enveloppe `vi.mocked` : un mock que `vi.mock` a posé sur le client et que le
 * test rend par `vi.mocked(api.x.y)` refuse lui aussi une valeur hors schéma.
 * La route se retrouve au moment de `mockResolvedValue`, car le test appelle
 * souvent `vi.mocked` à la racine du fichier, avant tout relevé.
 */
function garderMocked(): void {
  const courant: Mocked & { [MARQUE_MOCKED]?: true } = vi.mocked;
  if (courant[MARQUE_MOCKED]) return;
  const original: Mocked = vi.mocked.bind(vi);
  const garde = ((item: unknown, options?: object) => {
    if (typeof item === "function" && vi.isMockFunction(item)) {
      surveiller(item as unknown as Simulable, () => MOCKS_VUS.get(item));
    }
    return original(item as never, options as never);
  }) as unknown as Mocked & { [MARQUE_MOCKED]?: true };
  garde[MARQUE_MOCKED] = true;
  vi.mocked = garde;
}

/** Pose le garde sur `vi.spyOn` et `vi.mocked` ; à appeler une fois, depuis le fichier de setup. */
export function installerLeGarde(): void {
  garderSpyOn();
  garderMocked();
  beforeEach(releverLesMocks);
}
