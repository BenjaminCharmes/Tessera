import { describe, expect, it } from "vitest";
import { CONFRONTATIONS, schemaVise } from "./champs";
import { proprietes, reponseDecrite, routesDuSchema } from "./openapi";
import { HORS_PERIMETRE, SANS_SCHEMA } from "./perimetre";
import { APPELS, routesCouvertes } from "./registre";

describe("types declared by the frontend against the backend schema", () => {
  it.each(CONFRONTATIONS.map((c) => [c.libelle, c] as const))(
    "%s declares exactly the fields of its schema",
    (_libelle, c) => {
      const ecartes = Object.keys(c.ecartes ?? {});
      const duSchema = proprietes(schemaVise(c)).filter((nom) => !ecartes.includes(nom)).sort();

      // Un champ du schéma absent du type (`arretes`) ou un champ inventé.
      expect(c.declares).toEqual(duSchema);
    },
  );

  it("names every field it leaves out on purpose, and the schema still has it", () => {
    for (const c of CONFRONTATIONS) {
      for (const [nom, raison] of Object.entries(c.ecartes ?? {})) {
        expect(raison.length, `${c.libelle}.${nom}`).toBeGreaterThan(0);
        expect(proprietes(schemaVise(c)), `${c.libelle}.${nom}`).toContain(nom);
      }
    }
  });
});

describe("perimeter of the contract", () => {
  const couvertes = routesCouvertes();
  const toutes = routesDuSchema().sort();

  it("lists every route of the schema as covered or as not covered, once", () => {
    const classees = [...couvertes, ...SANS_SCHEMA, ...HORS_PERIMETRE].sort();

    expect(classees).toEqual(toutes);
  });

  it("covers the routes the ticket names", () => {
    expect(couvertes).toEqual(
      expect.arrayContaining([
        "GET /api/v1/runs/{run_id}",
        "GET /api/v1/projects/{project_id}/usage/breakdown",
        "GET /api/v1/projects/{project_id}/services",
        "POST /api/v1/projects/{project_id}/services/start",
        "POST /api/v1/projects/{project_id}/services/stop",
        "GET /api/v1/projects/{project_id}/branches/cleanup",
        "POST /api/v1/projects/{project_id}/branches/cleanup",
        "GET /api/v1/usage/quota",
      ]),
    );
  });

  it("covers only routes whose response the schema describes", () => {
    for (const a of APPELS) expect(reponseDecrite(a.verbe, a.route), a.nom).toBe(true);
  });

  it("keeps in the no-schema list only routes whose response the schema leaves open", () => {
    for (const entree of SANS_SCHEMA) {
      const [verbe, route] = entree.split(" ");
      expect(reponseDecrite(verbe.toLowerCase(), route), entree).toBe(false);
    }
  });
});
