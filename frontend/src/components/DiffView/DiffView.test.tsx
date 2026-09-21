import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DiffView from "./index";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

const diff = vi.mocked(api.tickets.diff);

describe("DiffView", () => {
  beforeEach(() => {
    diff.mockReset();
  });

  it("montre le diff, un fichier a la fois, avec ses compteurs", async () => {
    diff.mockResolvedValue({
      ticket_id: "ticket-001",
      branch: "ticket-001-x",
      commit: null,
      diff: [
        "diff --git a/app.py b/app.py",
        "@@ -1 +1 @@",
        "-x = 1",
        "+x = 2",
      ].join("\n"),
      files: ["app.py"],
    });

    render(<DiffView projectId="p" ticketId="ticket-001" />);

    expect(await screen.findByText("app.py")).toBeInTheDocument();
    expect(screen.getByText("+1")).toBeInTheDocument();
    expect(screen.getByText("-1")).toBeInTheDocument();
    expect(screen.getByText("+x = 2")).toBeInTheDocument();
  });

  it("permet de passer d'un fichier a l'autre", async () => {
    // Panne d'usage : tout etait concatene dans un seul tampon, sans
    // navigation ni couleur. Sur cinq fichiers dont deux longs Markdown, on ne
    // lisait rien (ticket-075).
    diff.mockResolvedValue({
      ticket_id: "ticket-001",
      branch: "ticket-001-x",
      commit: null,
      diff: [
        "diff --git a/app.py b/app.py",
        "@@ -1 +1 @@",
        "+depuis app",
        "diff --git a/README.md b/README.md",
        "@@ -1 +1 @@",
        "+depuis readme",
      ].join("\n"),
      files: ["app.py", "README.md"],
    });

    render(<DiffView projectId="p" ticketId="ticket-001" />);

    expect(await screen.findByText("+depuis app")).toBeInTheDocument();
    expect(screen.queryByText("+depuis readme")).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: /README/ }));

    expect(screen.getByText("+depuis readme")).toBeInTheDocument();
  });
  it("dit qu'un ticket jamais lance n'a pas de branche", async () => {
    diff.mockResolvedValue({
      ticket_id: "ticket-002", branch: null, commit: null, diff: "", files: [],
    });

    render(<DiffView projectId="p" ticketId="ticket-002" />);

    expect(await screen.findByText(/jamais été lancé/i)).toBeInTheDocument();
  });

  it("distingue une branche sans rien dedans d'un ticket jamais lance", async () => {
    // C'est exactement le cas vecu le 2026-09-17 : deux runs `done`, deux
    // branches creees, aucun commit. L'ecran doit le dire.
    diff.mockResolvedValue({
      ticket_id: "ticket-003", branch: "ticket-003-x", commit: null, diff: "", files: [],
    });

    render(<DiffView projectId="p" ticketId="ticket-003" />);

    expect(await screen.findByText(/n'a rien produit/i)).toBeInTheDocument();
    expect(screen.getByText("ticket-003-x")).toBeInTheDocument();
  });

  it("montre le diff quand la branche a ete supprimee mais le commit existe", async () => {
    // ticket-116 : supprimer la branche apres le merge est la pratique
    // normale. L'ecran annoncait « jamais lance », ce qui etait faux — le
    // travail est dans l'historique.
    diff.mockResolvedValue({
      ticket_id: "ticket-004",
      branch: null,
      commit: "abc123def456",
      diff: [
        "diff --git a/app.py b/app.py",
        "@@ -1 +1 @@",
        "-x = 1",
        "+x = 42",
      ].join("\n"),
      files: ["app.py"],
    });

    render(<DiffView projectId="p" ticketId="ticket-004" />);

    expect(await screen.findByText("+x = 42")).toBeInTheDocument();
    expect(screen.queryByText(/jamais été lancé/i)).toBeNull();
    expect(screen.getByText(/commit abc123def456/)).toBeInTheDocument();
  });
});
