import { describe, expect, it } from "vitest";
import { TYPES_NOTIF } from "./notifications";
import {
  estReglagesParType,
  LIBELLES_TYPE,
  reglagesParDefaut,
} from "./reglagesNotifications";

describe("reglagesNotifications", () => {
  it("defaults to the system everywhere and a sound for questions and red CI", () => {
    const r = reglagesParDefaut();
    for (const type of TYPES_NOTIF) expect(r[type].systeme).toBe(true);
    const avecSon = TYPES_NOTIF.filter((t) => r[t].son);
    expect(avecSon).toEqual(["question", "ci_rouge"]);
  });

  it("labels every type", () => {
    for (const type of TYPES_NOTIF) expect(LIBELLES_TYPE[type]).not.toBe("");
  });

  it("accepts the defaults and refuses a missing type or a wrong value", () => {
    const r = reglagesParDefaut();
    expect(estReglagesParType(r)).toBe(true);
    const incomplet: Partial<typeof r> = { ...r };
    delete incomplet.quota_bas;
    expect(estReglagesParType(incomplet)).toBe(false);
    expect(estReglagesParType({ ...r, question: { systeme: "oui", son: true } })).toBe(false);
    expect(estReglagesParType(null)).toBe(false);
  });
});
