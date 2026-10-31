import { resoudre, type Schema } from "./openapi";

function genre(valeur: unknown): string {
  if (valeur === null) return "null";
  if (Array.isArray(valeur)) return "array";
  if (Number.isInteger(valeur)) return "integer";
  return typeof valeur;
}

function accepte(schema: Schema, genreDeLaValeur: string): boolean {
  if (schema.type === "number") return genreDeLaValeur === "number" || genreDeLaValeur === "integer";
  return schema.type === genreDeLaValeur;
}

function validerObjet(schema: Schema, valeur: Record<string, unknown>, chemin: string): string[] {
  const proprietes = schema.properties ?? {};
  const erreurs: string[] = [];
  for (const requis of schema.required ?? []) {
    if (!(requis in valeur)) erreurs.push(`${chemin}.${requis} : champ requis absent`);
  }
  for (const [cle, enfant] of Object.entries(valeur)) {
    const attendu = proprietes[cle] ?? (typeof schema.additionalProperties === "object" ? schema.additionalProperties : undefined);
    if (attendu === undefined) erreurs.push(`${chemin}.${cle} : champ que le schéma ne décrit pas`);
    else erreurs.push(...valider(attendu, enfant, `${chemin}.${cle}`));
  }
  return erreurs;
}

function validerTableau(schema: Schema, valeur: unknown[], chemin: string): string[] {
  return valeur.flatMap((element, rang) => {
    const attendu = schema.prefixItems?.[rang] ?? schema.items;
    return attendu === undefined ? [] : valider(attendu, element, `${chemin}[${rang}]`);
  });
}

/** Les écarts entre `valeur` et `schema`, un message par écart ; vide quand elle est conforme. */
export function valider(schema: Schema, valeur: unknown, chemin = "$"): string[] {
  const attendu = resoudre(schema);
  if (attendu.anyOf !== undefined) {
    const essais = attendu.anyOf.map((option) => valider(option, valeur, chemin));
    return essais.some((erreurs) => erreurs.length === 0) ? [] : essais[0];
  }
  const trouve = genre(valeur);
  if (!accepte(attendu, trouve)) return [`${chemin} : ${attendu.type ?? "?"} attendu, ${trouve} reçu`];
  if (attendu.enum !== undefined && !attendu.enum.includes(valeur)) {
    return [`${chemin} : ${JSON.stringify(valeur)} hors de ${JSON.stringify(attendu.enum)}`];
  }
  if (Array.isArray(valeur)) return validerTableau(attendu, valeur, chemin);
  if (trouve === "object") return validerObjet(attendu, valeur as Record<string, unknown>, chemin);
  return [];
}

function exempleDObjet(schema: Schema): Record<string, unknown> {
  if (schema.properties === undefined && typeof schema.additionalProperties === "object") {
    return { exemple: exempleDe(schema.additionalProperties) };
  }
  return Object.fromEntries(Object.entries(schema.properties ?? {}).map(([cle, enfant]) => [cle, exempleDe(enfant)]));
}

/** Une valeur minimale conforme à `schema` : chaque champ présent, un élément par tableau. */
export function exempleDe(schema: Schema): unknown {
  const attendu = resoudre(schema);
  if (attendu.anyOf !== undefined) {
    return exempleDe(attendu.anyOf.find((option) => option.type !== "null") ?? attendu.anyOf[0]);
  }
  if (attendu.enum !== undefined) return attendu.enum[0];
  switch (attendu.type) {
    case "object":
      return exempleDObjet(attendu);
    case "array":
      return attendu.prefixItems
        ? attendu.prefixItems.map(exempleDe)
        : attendu.items
          ? [exempleDe(attendu.items)]
          : [];
    case "integer":
      return 1;
    case "number":
      return 1.5;
    case "boolean":
      return false;
    case "null":
      return null;
    default:
      return "exemple";
  }
}
