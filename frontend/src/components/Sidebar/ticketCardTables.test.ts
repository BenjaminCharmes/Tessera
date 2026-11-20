import { describe, expect, it } from "vitest";
import { STATUS_STYLE } from "./ticketCardTables";

describe("STATUS_STYLE", () => {
  it("uses a 12% tinted background and no solid one", () => {
    for (const style of Object.values(STATUS_STYLE)) {
      expect(style).toMatch(/bg-\w+-500\/12/);
      expect(style).not.toMatch(/-(900|800|700)\b/);
    }
  });
});
