import { afterEach, describe, expect, it, vi } from "vitest";
import { logger } from "./logger";

/**
 * Le logger structuré du frontend — ticket-251.
 *
 * La convention interdisait `console.log` sans fournir d'outil : ce module
 * est le seul point de sortie autorisé (ESLint `no-console` partout ailleurs),
 * et sa sortie est une ligne JSON, pas une chaîne libre.
 */
describe("logger", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it.each(["debug", "info", "warn", "error"] as const)(
    "émet une ligne JSON datée avec niveau et contexte — %s",
    (level) => {
      const spy = vi.spyOn(console, level).mockImplementation(() => {});

      logger[level]("message de test", { code: 42 });

      expect(spy).toHaveBeenCalledTimes(1);
      const ligne: unknown = JSON.parse(spy.mock.calls[0][0] as string);
      expect(ligne).toMatchObject({
        level,
        msg: "message de test",
        code: 42,
      });
      expect(typeof (ligne as { ts: unknown }).ts).toBe("string");
    },
  );

  it("émet sans contexte quand on n'en donne pas", () => {
    const spy = vi.spyOn(console, "info").mockImplementation(() => {});

    logger.info("seul");

    const ligne: unknown = JSON.parse(spy.mock.calls[0][0] as string);
    expect(ligne).toMatchObject({ level: "info", msg: "seul" });
  });
});
