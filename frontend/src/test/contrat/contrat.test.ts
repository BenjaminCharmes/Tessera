import { describe, expect, it } from "vitest";
import { CONFRONTATIONS, facultatifsExiges, schemaVise } from "./champs";
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

  it("declares no field optional that the schema requires", () => {
    for (const c of CONFRONTATIONS) expect(facultatifsExiges(c), c.libelle).toEqual([]);
  });

  it("fails the comparison when a required field is optional in the type", () => {
    const service = CONFRONTATIONS.find((c) => c.libelle === "ServiceActif (liste)");
    if (service === undefined) throw new Error("confrontation « ServiceActif (liste) » absente");

    const infidele = { ...service, facultatifs: ["sortie", "arrete_a_la_main"] };

    expect(facultatifsExiges(infidele)).toEqual(["sortie", "arrete_a_la_main"]);
  });

  it("only lists as optional fields the schema knows", () => {
    for (const c of CONFRONTATIONS) {
      for (const nom of c.facultatifs) expect(c.declares, `${c.libelle}.${nom}`).toContain(nom);
    }
  });

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
