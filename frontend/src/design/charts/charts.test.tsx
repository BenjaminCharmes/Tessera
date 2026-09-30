import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import TimeBars from "./TimeBars";
import TimeLines from "./TimeLines";
import Donut from "./Donut";
import ShareBars from "./ShareBars";
import { foldSlices, formatDay, niceMax, OTHER, SERIES } from "./palette";

const fmt = (n: number) => `${n}`;

describe("niceMax", () => {
  it("rounds up to 1, 2 or 5 times a power of ten", () => {
    expect(niceMax(0)).toBe(1);
    expect(niceMax(0.37)).toBe(0.5);
    expect(niceMax(3779)).toBe(5000);
    expect(niceMax(200)).toBe(200);
  });
});

describe("formatDay", () => {
  it("keeps the UTC day whatever the local time zone", () => {
    expect(formatDay("2026-09-01")).toMatch(/^1 /);
  });
});

describe("TimeBars", () => {
  it("says there is nothing to show when every value is zero", () => {
    render(<TimeBars label="Coût" points={[{ label: "a", value: 0 }]} format={fmt} empty="Rien" />);
    expect(screen.getByText("Rien")).toBeInTheDocument();
  });

  it("draws one bar per point and shows its value on hover", () => {
    render(
      <TimeBars
        label="Coût"
        points={[
          { label: "lun", value: 2 },
          { label: "mar", value: 5 },
        ]}
        format={(n) => `${n} $`}
        empty="Rien"
      />,
    );
    const bars = screen.getAllByTestId("bar");
    expect(bars).toHaveLength(2);
    fireEvent.mouseEnter(bars[1]);
    expect(screen.getByRole("tooltip")).toHaveTextContent("mar · 5 $");
  });
  it("keeps its screen-reader table inside a positioned box", () => {
    // `sr-only` doit être sur le div parent du <table>, pas sur le <table>
    // lui-même : un tableau ignore height:1px et overflow:hidden, ce qui
    // allongeait la page au-delà du dernier bloc visible.
    render(<TimeBars label="Coût" points={[{ label: "a", value: 1 }]} format={fmt} empty="Rien" />);
    const table = screen.getByRole("table", { hidden: true });
    expect(table.parentElement).toHaveClass("sr-only");
    expect(table.parentElement?.parentElement).toHaveClass("relative");
  });

  it("keeps its screen-reader table accessible with its caption", () => {
    render(<TimeBars label="Coût" points={[{ label: "a", value: 1 }]} format={fmt} empty="Rien" />);
    const table = screen.getByRole("table", { hidden: true });
    expect(table.querySelector("caption")).toBeInTheDocument();
  });
});

describe("TimeLines", () => {
  it("says there is nothing to show when every series is flat at zero", () => {
    render(
      <TimeLines labels={["a"]} series={[{ name: "in", values: [0] }]} format={fmt} empty="Rien" />,
    );
    expect(screen.getByText("Rien")).toBeInTheDocument();
  });

  it("draws one line per series with a legend", () => {
    render(
      <TimeLines
        labels={["a", "b"]}
        series={[
          { name: "Entrants", values: [1, 4] },
          { name: "Sortants", values: [2, 3] },
        ]}
        format={fmt}
        empty="Rien"
      />,
    );
    expect(screen.getAllByTestId("line")).toHaveLength(2);
    expect(screen.getAllByText("Entrants").length).toBeGreaterThan(0);
  });
});

describe("Donut", () => {
  it("folds everything past three slices into a neutral « autres »", () => {
    const parts = foldSlices([
      { key: "a", value: 4 },
      { key: "b", value: 3 },
      { key: "c", value: 2 },
      { key: "d", value: 1 },
      { key: "e", value: 1 },
    ]);
    expect(parts.map((p) => p.key)).toEqual(["a", "b", "c", "autres"]);
    expect(parts[3].value).toBe(2);
    expect(parts[3].color).toBe(OTHER);
    expect(parts[0].color).toBe(SERIES[0]);
  });

  it("says there is nothing to show without any value", () => {
    render(<Donut slices={[]} format={fmt} caption="total" empty="Rien" />);
    expect(screen.getByText("Rien")).toBeInTheDocument();
  });

  it("draws one slice per part and lists each share", () => {
    render(
      <Donut
        slices={[
          { key: "codeur", value: 3 },
          { key: "reviewer", value: 1 },
        ]}
        format={fmt}
        caption="total"
        empty="Rien"
      />,
    );
    expect(screen.getAllByTestId("slice")).toHaveLength(2);
    expect(screen.getByText("3 · 75 %")).toBeInTheDocument();
  });
});

describe("ShareBars", () => {
  it("says there is nothing to show without rows", () => {
    render(<ShareBars rows={[]} format={fmt} empty="Rien" />);
    expect(screen.getByText("Rien")).toBeInTheDocument();
  });

  it("shows each row with its share of the total", () => {
    render(
      <ShareBars
        rows={[
          { key: "alpha", value: 1, detail: "2 appels" },
          { key: "beta", value: 1 },
        ]}
        format={fmt}
        empty="Rien"
      />,
    );
    expect(screen.getByText("1 · 50 % · 2 appels")).toBeInTheDocument();
    expect(screen.getByText("beta")).toBeInTheDocument();
  });

  it("scales an average against the largest row, without a share", () => {
    render(
      <ShareBars
        rows={[
          { key: "codeur", value: 4 },
          { key: "reviewer", value: 2 },
        ]}
        format={(n) => `${n} s`}
        empty="Rien"
        scale="max"
      />,
    );
    expect(screen.getByText("4 s")).toBeInTheDocument();
    expect(screen.queryByText(/%/)).toBeNull();
  });
});
