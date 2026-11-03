import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FichiersView from "./index";
import { _viderCacheResource } from "../../hooks/useResource";
import type { DirEntry } from "../../lib/fs";
import type { Project, Ticket, TicketStatus } from "../../types/api";

// Monaco ne se charge pas sous jsdom : les deux vues lourdes sont doublées.
vi.mock("../Editor", () => ({
  default: (props: { openFilePath: string | null }) => (
    <div data-testid="editor">{props.openFilePath}</div>
  ),
}));
vi.mock("../DiffView", () => ({
  default: (props: { projectId: string; ticketId: string }) => (
    <div data-testid="diff-view">{`${props.projectId}/${props.ticketId}`}</div>
  ),
}));
vi.mock("../../lib/api");
vi.mock("../../lib/fs");
import { api } from "../../lib/api";
import { listEntries } from "../../lib/fs";

const diff = vi.mocked(api.tickets.diff);
const lister = vi.mocked(listEntries);

const entree = (path: string, is_dir = false): DirEntry => ({
  name: path.split("/").pop() ?? path,
  path,
  is_dir,
});

const ARBRE: Record<string, DirEntry[]> = {
  "/p": [entree("/p/src", true), entree("/p/README.md")],
  "/p/src": [entree("/p/src/app.py"), entree("/p/src/util.py")],
};

const projet: Project = {
  id: "p",
  name: "Demo",
  path: "/p",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

function ticket(id: string, status: TicketStatus = "done", created = "2026-01-01"): Ticket {
  return {
    id,
    title: id,
    status,
    type: "feat",
    priority: "medium",
    agent: "codeur",
    depends_on: [],
    created,
    github_issue_url: null,
    pr_number: null,
    body: "",
    project_id: "p",
    file_path: "",
  };
}

const VIDE: Record<TicketStatus, Ticket[]> = {
  todo: [],
  "in-progress": [],
  "in-review": [],
  done: [ticket("ticket-7", "done", "2026-02-01"), ticket("ticket-3")],
  blocked: [],
  cancelled: [],
};

function monter(surcharges: Partial<Parameters<typeof FichiersView>[0]> = {}) {
  const props = {
    project: projet,
    ticket: null,
    byStatus: VIDE,
    openFilePath: null,
    onOpenFile: vi.fn(),
    onCloseFile: vi.fn(),
    ...surcharges,
  };
  return { ...render(<FichiersView {...props} />), props };
}

describe("FichiersView", () => {
  beforeEach(() => {
    localStorage.clear();
    _viderCacheResource();
    diff.mockReset();
    lister.mockReset();
    lister.mockImplementation((chemin) => Promise.resolve(ARBRE[chemin] ?? []));
    diff.mockResolvedValue({
      ticket_id: "ticket-7",
      branch: "b",
      commit: null,
      diff: [
        "diff --git a/src/app.py b/src/app.py",
        "@@ -1 +1,2 @@",
        "-x = 1",
        "+x = 2",
        "+y = 3",
      ].join("\n"),
      files: ["src/app.py"],
    });
  });

  it("shows the search, the touched files and the recent files when nothing is open", async () => {
    localStorage.setItem("tessera.ui.fichiers-recents.p", JSON.stringify(["/p/README.md"]));
    monter();

    expect(screen.getByText("Aucun fichier ouvert")).toBeInTheDocument();
    expect(screen.getByLabelText("Rechercher un fichier")).toBeInTheDocument();
    // Sans ticket sélectionné : le dernier ticket terminé.
    expect(
      await screen.findByText("Touchés par le dernier run — ticket-7"),
    ).toBeInTheDocument();
    expect(await screen.findByText("src/app.py")).toBeInTheDocument();
    expect(screen.getByText("+2")).toBeInTheDocument();
    expect(screen.getByText("-1")).toBeInTheDocument();
    expect(diff).toHaveBeenCalledWith("p", "ticket-7");
    expect(screen.getByText("Ouverts récemment")).toBeInTheDocument();
    expect(screen.getByText("README.md")).toBeInTheDocument();
  });

  it("opens the file picked from the search results", async () => {
    const { props } = monter();

    await userEvent.type(screen.getByLabelText("Rechercher un fichier"), "UTIL");
    await userEvent.click(await screen.findByRole("button", { name: "src/util.py" }));

    expect(props.onOpenFile).toHaveBeenCalledWith("/p/src/util.py");
    expect(screen.queryByRole("button", { name: "src/app.py" })).toBeNull();
  });

  it("says so when no file matches the search", async () => {
    monter();
    await userEvent.type(screen.getByLabelText("Rechercher un fichier"), "zzz");
    expect(await screen.findByText("Aucun fichier ne correspond.")).toBeInTheDocument();
  });

  it("opens a file touched by the run from its path in the project", async () => {
    const { props } = monter();
    await userEvent.click(await screen.findByRole("button", { name: /src\/app\.py/ }));
    expect(props.onOpenFile).toHaveBeenCalledWith("/p/src/app.py");
  });

  it("renders the editor when a file is open", async () => {
    monter({ openFilePath: "/p/README.md" });
    expect(await screen.findByTestId("editor")).toHaveTextContent("/p/README.md");
    expect(screen.queryByText("Aucun fichier ouvert")).toBeNull();
  });

  it("renders the diff of the selected ticket in the diff mode", async () => {
    monter({ ticket: ticket("ticket-5", "in-review") });
    await userEvent.click(screen.getByRole("button", { name: "Diff du ticket" }));
    expect(await screen.findByTestId("diff-view")).toHaveTextContent("p/ticket-5");
  });

  it("invites to select a ticket in the diff mode when none is selected", async () => {
    monter();
    await userEvent.click(screen.getByRole("button", { name: "Diff du ticket" }));
    expect(
      screen.getByText("Sélectionne un ticket pour voir son diff"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("diff-view")).toBeNull();
  });

  it("focuses the search on Ctrl+P, and only while the view is mounted", () => {
    const { unmount } = monter();
    const prevenu = !fireEvent.keyDown(window, { key: "p", ctrlKey: true });
    expect(prevenu).toBe(true);
    expect(screen.getByLabelText("Rechercher un fichier")).toHaveFocus();

    unmount();
    expect(fireEvent.keyDown(window, { key: "p", ctrlKey: true })).toBe(true);
  });

  it("closes the open file on Ctrl+P so the search can take focus", () => {
    const { props } = monter({ openFilePath: "/p/README.md" });
    fireEvent.keyDown(window, { key: "p", ctrlKey: true });
    expect(props.onCloseFile).toHaveBeenCalledTimes(1);
  });

  it("asks for a project when none is active", () => {
    monter({ project: null });
    expect(
      screen.getByText("Sélectionne un projet pour parcourir ses fichiers."),
    ).toBeInTheDocument();
  });
});
