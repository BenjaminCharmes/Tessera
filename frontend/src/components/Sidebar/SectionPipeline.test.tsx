import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SectionPipeline from "./SectionPipeline";

vi.mock("./PanneauPipeline", () => ({
  default: ({ projectId }: { projectId: string }) => (
    <div>réglage de {projectId}</div>
  ),
}));

describe("SectionPipeline", () => {
  it("porte un chevron, comme les autres sections repliables (ticket-205)", () => {
    // Un simple libellé gris ne se lisait pas comme un bouton : la section
    // passait inaperçue.
    render(<SectionPipeline projectId="lyra" runEnCours={false} />);

    const bouton = screen.getByRole("button", { name: "Pipeline" });
    expect(bouton.getAttribute("aria-expanded")).toBe("false");
    expect(bouton.querySelector("svg")).not.toBeNull();
    expect(screen.queryByText("réglage de lyra")).not.toBeInTheDocument();
  });

  it("déplie le réglage du projet sur un clic", async () => {
    render(<SectionPipeline projectId="lyra" runEnCours={false} />);

    await userEvent.click(screen.getByRole("button", { name: "Pipeline" }));

    expect(screen.getByText("réglage de lyra")).toBeInTheDocument();
  });
});
