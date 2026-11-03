import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { useZoomDuBureau } from "./useZoomDuBureau";

/** Une vue qui, comme la Supervision, ne monte ses pièces qu'une fois connectée. */
function Vue({ montee }: { montee: boolean }) {
  const { zoom, largeur, setMode, conteneur, contenu } = useZoomDuBureau({ cle: "essai.zoom", lignes: 3 });
  return (
    <div>
      <output data-testid="zoom">{zoom}</output>
      <output data-testid="largeur">{largeur ?? "aucune"}</output>
      <button type="button" onClick={() => setMode(0.4)}>min</button>
      <button type="button" onClick={() => setMode(1.25)}>max</button>
      {montee && (
        <div ref={conteneur} data-essai="conteneur">
          <div ref={contenu} data-zoom={zoom} data-essai="contenu">
            {[0, 1, 2, 3].map((i) => (
              <section key={i} data-ligne-du-zoom data-bas={(i + 1) * 300} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/** Une boîte DOMRect minimale : seuls `top` et `bottom` comptent ici. */
function boite(top: number, bottom: number): DOMRect {
  return { top, bottom, height: bottom - top, left: 0, right: 0, width: 0, x: 0, y: top, toJSON: () => ({}) };
}

beforeEach(() => {
  window.localStorage.clear();
  // jsdom ne calcule aucune mise en page : le conteneur fait 924 px (900 utiles), chaque ligne 300 px.
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockImplementation(function (this: HTMLElement) {
    return this.dataset.essai === "conteneur" ? 924 : 0;
  });
  // Le conteneur fait 1224 px de large, padding compris : 1200 px de mise en page.
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(function (this: HTMLElement) {
    return this.dataset.essai === "conteneur" ? 1224 : 0;
  });
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
    if (this.dataset.essai === "contenu") return boite(0, 1200);
    const bas = Number(this.dataset.bas ?? 0);
    return boite(bas - 300, bas);
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useZoomDuBureau", () => {
  it("applies the three-row zoom once the rooms mount after the view", () => {
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockImplementation(function (this: HTMLElement) {
      return this.dataset.essai === "conteneur" ? 474 : 0;
    });
    const { rerender } = render(<Vue montee={false} />);
    expect(screen.getByTestId("zoom")).toHaveTextContent(/^1$/);

    rerender(<Vue montee />);

    // 450 px utiles pour trois lignes de 300 px : zoom 0,5, appliqué aux pièces.
    expect(screen.getByTestId("zoom")).toHaveTextContent(/^0\.5$/);
    expect(document.querySelector("[data-essai='contenu']")).toHaveAttribute("data-zoom", "0.5");
  });

  it("fits the rows measured on the mounted nodes, not a stale default", () => {
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockImplementation(function (this: HTMLElement) {
      return this.dataset.essai === "conteneur" ? 744 : 0;
    });
    const { rerender } = render(<Vue montee={false} />);

    rerender(<Vue montee />);

    // 720 px utiles pour 900 px de lignes : zoom 0,8.
    expect(screen.getByTestId("zoom")).toHaveTextContent(/^0\.8$/);
  });

  it("measures again after the rooms unmount and mount anew", () => {
    const { rerender } = render(<Vue montee />);
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockImplementation(function (this: HTMLElement) {
      return this.dataset.essai === "conteneur" ? 564 : 0;
    });

    rerender(<Vue montee={false} />);
    rerender(<Vue montee />);

    // 540 px utiles pour 900 px de lignes : zoom 0,6.
    expect(screen.getByTestId("zoom")).toHaveTextContent(/^0\.6$/);
  });

  it("never grows past 100 % to fit the rows: a wider Bureau would scroll sideways", () => {
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockImplementation(function (this: HTMLElement) {
      return this.dataset.essai === "conteneur" ? 1424 : 0;
    });
    render(<Vue montee />);

    expect(screen.getByTestId("zoom")).toHaveTextContent(/^1$/);
  });

  it("keeps one reference layout width from the minimum to the maximum zoom, so nothing reflows", () => {
    render(<Vue montee />);
    const largeur = screen.getByTestId("largeur").textContent;
    expect(largeur).toBe("1200");

    fireEvent.click(screen.getByRole("button", { name: "min" }));
    expect(screen.getByTestId("zoom")).toHaveTextContent(/^0\.4$/);
    expect(screen.getByTestId("largeur")).toHaveTextContent(largeur ?? "");

    fireEvent.click(screen.getByRole("button", { name: "max" }));
    expect(screen.getByTestId("zoom")).toHaveTextContent(/^1\.25$/);
    expect(screen.getByTestId("largeur")).toHaveTextContent(largeur ?? "");
  });
});
