import { vi } from "vitest";
import { schemaDeLaReponse } from "./openapi";
import { appelDe, type Appel } from "./registre";
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

function surveiller(espion: Simulable, appel: Appel): void {
  const unique = espion.mockResolvedValueOnce.bind(espion);
  const durable = espion.mockResolvedValue.bind(espion);
  espion.mockResolvedValue = (valeur) => {
    exigerConforme(appel, valeur);
    return durable(valeur);
  };
  espion.mockResolvedValueOnce = (valeur) => {
    exigerConforme(appel, valeur);
    return unique(valeur);
  };
}

type SpyOn = typeof vi.spyOn;
const MARQUE = Symbol.for("tessera.contrat.garde");

/**
 * Enveloppe `vi.spyOn` : un espion posé sur une fonction du périmètre refuse
 * toute valeur que `mockResolvedValue` lui donne hors du schéma de sa route.
 * Un `mockImplementation` n'est pas gardé : le contrat le dit dans `perimetre.ts`.
 */
export function installerLeGarde(): void {
  const courant: SpyOn & { [MARQUE]?: true } = vi.spyOn;
  if (courant[MARQUE]) return;
  const original: SpyOn = vi.spyOn.bind(vi);
  const garde = ((...args: Parameters<SpyOn>) => {
    const espion = original(...args);
    const appel = appelDe(args[0], String(args[1]));
    if (appel !== undefined) surveiller(espion as unknown as Simulable, appel);
    return espion;
  }) as unknown as SpyOn & { [MARQUE]?: true };
  garde[MARQUE] = true;
  vi.spyOn = garde;
}
