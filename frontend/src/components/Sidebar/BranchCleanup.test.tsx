import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BranchCleanup from "./BranchCleanup";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

const plan = vi.mocked(api.git.cleanupPlan);
const nettoyer = vi.mocked(api.git.cleanup);

describe("BranchCleanup", () => {
  beforeEach(() => {
    plan.mockReset();
    nettoyer.mockReset();
  });

  it("annonce ce qui partira avant qu'on agisse", async () => {
    plan.mockResolvedValue({
      nettoyables: ["ticket-001-rien", "chat/20260917"],
      conservees: [["ticket-002-x", "porte du travail absent de la base"]],
    });

    render(<BranchCleanup projectId="p" />);

    expect(await screen.findByText("ticket-001-rien")).toBeInTheDocument();
    expect(screen.getByText("chat/20260917")).toBeInTheDocument();
  });

  it("dit pourquoi une branche est conservee", async () => {
    plan.mockResolvedValue({
      nettoyables: [],
      conservees: [["ticket-002-x", "porte du travail absent de la base"]],
    });

    render(<BranchCleanup projectId="p" />);

    expect(await screen.findByText(/porte du travail/i)).toBeInTheDocument();
  });

  it("ne supprime rien sans clic explicite", async () => {
    plan.mockResolvedValue({ nettoyables: ["ticket-001-rien"], conservees: [] });

    render(<BranchCleanup projectId="p" />);
    await screen.findByText("ticket-001-rien");

    expect(nettoyer).not.toHaveBeenCalled();
  });

  it("supprime les branches du plan au clic", async () => {
    plan.mockResolvedValue({ nettoyables: ["ticket-001-rien"], conservees: [] });
    nettoyer.mockResolvedValue(["ticket-001-rien"]);

    render(<BranchCleanup projectId="p" />);
    await userEvent.click(await screen.findByRole("button", { name: /supprimer/i }));

    expect(nettoyer).toHaveBeenCalledWith("p", ["ticket-001-rien"]);
    expect(await screen.findByText(/1 branche supprimée/i)).toBeInTheDocument();
  });

  it("ne montre rien quand il n'y a rien a nettoyer", async () => {
    plan.mockResolvedValue({ nettoyables: [], conservees: [] });

    const { container } = render(<BranchCleanup projectId="p" />);

    await vi.waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
