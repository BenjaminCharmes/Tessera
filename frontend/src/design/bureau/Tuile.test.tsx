import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import DefsDuBureau from "./DefsDuBureau";
import Tuile from "./Tuile";

describe("Tuile", () => {
  it("paints its surface with one rect from the shared pattern of its moment", () => {
    const { container } = render(
      <>
        <DefsDuBureau />
        <Tuile motif="mur" moment="jour" />
        <Tuile motif="mur" moment="nuit" />
      </>,
    );
    const rects = container.querySelectorAll("[data-tuile=mur] rect");
    expect([...rects].map((r) => r.getAttribute("fill"))).toEqual(["url(#tuile-mur-jour)", "url(#tuile-mur-nuit)"]);
    expect(container.querySelector("pattern#tuile-mur-jour")).not.toBeNull();
  });

  it("declares the night pattern under the night moment, where its colours resolve", () => {
    const { container } = render(
      <>
        <DefsDuBureau />
        <Tuile motif="sol" moment="nuit" />
      </>,
    );
    expect(container.querySelector('[data-moment="nuit"] pattern#tuile-sol-nuit')).not.toBeNull();
    expect(container.querySelector('[data-moment="nuit"] pattern#tuile-sol-jour')).toBeNull();
  });
});
