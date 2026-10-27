import { describe, expect, it } from "vitest";
import { libelleDeSuite } from "./etapeDeSuite";

describe("libelleDeSuite", () => {
  it("names the documentation step", () => {
    expect(libelleDeSuite("documentation")).toBe("documentation");
  });

  it("names the delivery step without inventing sub-steps", () => {
    expect(libelleDeSuite("livraison")).toBe("livraison : rebase, tests, PR");
  });

  it.each(["securite", "validation", "tests", "", null])("says nothing for %s", (etape) => {
    expect(libelleDeSuite(etape)).toBeNull();
  });
});
