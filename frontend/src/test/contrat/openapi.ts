import { readFileSync } from "node:fs";
import { resolve } from "node:path";

/** Le morceau de JSON Schema que les routes du backend emploient. */
export interface Schema {
  $ref?: string;
  type?: string;
  properties?: Record<string, Schema>;
  required?: string[];
  items?: Schema;
  prefixItems?: Schema[];
  anyOf?: Schema[];
  additionalProperties?: Schema | boolean;
  enum?: unknown[];
}

interface Operation {
  responses: Record<string, { content?: Record<string, { schema: Schema }> }>;
}

interface Document {
  paths: Record<string, Record<string, Operation>>;
  components: { schemas: Record<string, Schema> };
}

// Le fichier versionné que `python -m tessera.openapi_export` régénère : un
// test backend échoue quand il est périmé, donc ce que lit le front est ce que
// sert le backend.
const CHEMIN = resolve(import.meta.dirname, "../../../../docs/openapi.json");

const document: Document = JSON.parse(readFileSync(CHEMIN, "utf-8"));

/** Suit un `$ref` jusqu'au schéma nommé ; un schéma sans `$ref` est rendu tel quel. */
export function resoudre(schema: Schema): Schema {
  if (schema.$ref === undefined) return schema;
  const nom = schema.$ref.replace("#/components/schemas/", "");
  const trouve = document.components.schemas[nom];
  if (trouve === undefined) throw new Error(`Schéma inconnu : ${schema.$ref}`);
  return resoudre(trouve);
}

/** Le schéma de la réponse 200 d'une route, `$ref` non suivi. */
export function schemaDeLaReponse(verbe: string, route: string): Schema {
  const operation = document.paths[route]?.[verbe];
  const schema = operation?.responses["200"]?.content?.["application/json"]?.schema;
  if (schema === undefined) throw new Error(`Aucune réponse JSON pour ${verbe.toUpperCase()} ${route}`);
  return schema;
}

/** Les routes que le schéma décrit, au format `GET /api/v1/…`. */
export function routesDuSchema(): string[] {
  return Object.entries(document.paths).flatMap(([route, verbes]) =>
    Object.keys(verbes).map((verbe) => `${verbe.toUpperCase()} ${route}`),
  );
}

/** Vrai quand la réponse 200 décrit sa forme : un objet sans propriété (`dict[str, object]`) n'en décrit aucune. */
export function reponseDecrite(verbe: string, route: string): boolean {
  const schema = document.paths[route]?.[verbe]?.responses["200"]?.content?.["application/json"]?.schema;
  if (schema === undefined) return false;
  const attendu = resoudre(schema);
  return attendu.type !== "object" || attendu.properties !== undefined;
}

/** Les noms de propriétés d'un schéma objet. */
export function proprietes(schema: Schema): string[] {
  return Object.keys(resoudre(schema).properties ?? {});
}
