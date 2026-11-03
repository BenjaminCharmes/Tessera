import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { SanteAgent } from "../../lib/santeAgent";
import Bulle from "./Bulle";

describe("Bulle", () => {
  it("renders nothing for an agent that works", () => {
    const { container } = render(<Bulle sante="actif" />);

    expect(container).toBeEmptyDOMElement();
  });

  it.each<[SanteAgent, string]>([
    ["attente", "…"],
    ["question", "?"],
    ["blocage_suspecte", "!"],
  ])("renders only the sign for %s", (sante, signe) => {
    render(<Bulle sante={sante} />);

    expect(screen.getByTestId("bulle").textContent).toBe(signe);
    expect(screen.getByTestId("bulle")).toHaveAttribute("aria-hidden", "true");
  });
});
