import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { IconEngrenage, IconSettings } from "./icons";

describe("icons", () => {
  it("icon_engrenage_renders_an_aria_hidden_svg", () => {
    const { container } = render(<IconEngrenage size={20} />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg).toHaveAttribute("width", "20");
    // Une roue dentée : un contour et un moyeu percé, pas des rayons.
    expect(svg?.querySelector("circle")).not.toBeNull();
    expect(svg?.querySelectorAll("path")).toHaveLength(1);
  });

  it("leaves_icon_settings_untouched", () => {
    const { container } = render(<IconSettings />);
    expect(container.querySelectorAll("path")).toHaveLength(1);
    expect(container.querySelector("circle")).toHaveAttribute("r", "3");
  });
});
