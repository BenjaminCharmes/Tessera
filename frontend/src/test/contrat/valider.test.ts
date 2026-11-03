import { describe, expect, it } from "vitest";
import type { Schema } from "./openapi";
import { exempleDe, valider } from "./valider";

const OBJET: Schema = {
  type: "object",
  properties: {
    nom: { type: "string" },
    pid: { anyOf: [{ type: "integer" }, { type: "null" }] },
    etat: { type: "string", enum: ["a", "b"] },
    tailles: { type: "array", items: { type: "number" } },
  },
  required: ["nom"],
};

describe("valider", () => {
  it("accepts a conforming value", () => {
    expect(valider(OBJET, { nom: "x", pid: null, etat: "a", tailles: [1, 2.5] })).toEqual([]);
  });

  it("reports a missing required field, an unknown one and a wrong type", () => {
    expect(valider(OBJET, {})).toEqual(["$.nom : champ requis absent"]);
    expect(valider(OBJET, { nom: "x", autre: 1 })[0]).toContain("autre");
    expect(valider(OBJET, { nom: 3 })[0]).toContain("string attendu");
  });

  it("tells an array from an object", () => {
    expect(valider(OBJET, [])[0]).toContain("object attendu, array reçu");
    expect(valider({ type: "array", items: { type: "string" } }, {})[0]).toContain("array attendu");
  });

  it("checks nested items, enum members and integers", () => {
    expect(valider(OBJET, { nom: "x", tailles: ["1"] })[0]).toContain("$.tailles[0]");
    expect(valider(OBJET, { nom: "x", etat: "c" })[0]).toContain("hors de");
    expect(valider(OBJET, { nom: "x", pid: 1.5 })).not.toEqual([]);
  });

  it("checks the values of a map and the slots of a tuple", () => {
    const table: Schema = { type: "object", additionalProperties: { type: "number" } };
    const paire: Schema = { type: "array", prefixItems: [{ type: "string" }, { type: "string" }] };

    expect(valider(table, { a: 1 })).toEqual([]);
    expect(valider(table, { a: "1" })).not.toEqual([]);
    expect(valider(paire, ["x", 2])[0]).toContain("[1]");
  });
});

describe("exempleDe", () => {
  it("builds a value that the schema accepts", () => {
    const exemple = exempleDe(OBJET);

    expect(valider(OBJET, exemple)).toEqual([]);
    expect(exemple).toEqual({ nom: "exemple", pid: 1, etat: "a", tailles: [1.5] });
  });

  it("gives one entry to a map and a full tuple", () => {
    expect(exempleDe({ type: "object", additionalProperties: { type: "boolean" } })).toEqual({ exemple: false });
    expect(exempleDe({ type: "array", prefixItems: [{ type: "string" }, { type: "integer" }] })).toEqual(["exemple", 1]);
  });
});
