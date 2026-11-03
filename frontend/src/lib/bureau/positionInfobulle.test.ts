import { describe, expect, it } from "vitest";
import { positionInfobulle } from "./positionInfobulle";

const FENETRE = { largeur: 1000, hauteur: 800 };
const INFOBULLE = { largeur: 200, hauteur: 100 };

describe("positionInfobulle", () => {
  it("puts the tooltip above the anchor when there is room", () => {
    const position = positionInfobulle({ top: 400, bottom: 460, left: 50 }, INFOBULLE, FENETRE);

    expect(position).toEqual({ top: 296, left: 50 });
  });

  it("puts it below the anchor when the top of the window would cut it", () => {
    const position = positionInfobulle({ top: 60, bottom: 120, left: 50 }, INFOBULLE, FENETRE);

    expect(position.top).toBe(124);
  });

  it("keeps it inside the right edge", () => {
    const position = positionInfobulle({ top: 400, bottom: 460, left: 950 }, INFOBULLE, FENETRE);

    expect(position.left).toBe(796);
  });

  it("never goes past the left edge", () => {
    const position = positionInfobulle({ top: 400, bottom: 460, left: -30 }, INFOBULLE, FENETRE);

    expect(position.left).toBe(4);
  });
});
