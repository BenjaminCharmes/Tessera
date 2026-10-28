import { afterEach, describe, expect, it, vi } from "vitest";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import BoiteAuxLettres from "./BoiteAuxLettres";
import { api } from "../../lib/api";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import { _viderCacheResource } from "../../hooks/useResource";
import type { EventType, PRStatusEntry } from "../../types/api";

function ev(type: EventType, data: Record<string, unknown> = {}) {
  return {
    type,
    agent: null,
    ticket_id: "ticket-001",
    data,
    timestamp: "2026-10-24T10:00:00.000Z",
  };
}

function rejouer(...evenements: ReturnType<typeof ev>[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

const livraison = (data: Record<string, unknown> = {}) =>
  ev("livraison_done", {
    pr_number: 42,
    arret: null,
    conflits: [],
    merged: false,
    ...data,
  });

function entree(over: Partial<PRStatusEntry> = {}): PRStatusEntry {
  return {
    ticket_id: "ticket-001",
    state: "open",
    ci_status: "pending",
    pr_url: "https://example.test/org/repo/pull/42",
    pr_number: 42,
    ...over,
  };
}

function etatAvecTicket(): StreamState {
  return rejouer(ev("agent_started"));
}

afterEach(() => {
  vi.restoreAllMocks();
  _viderCacheResource();
});

describe("BoiteAuxLettres", () => {
  const CAS: [string, StreamState, string][] = [
    ["none", INITIAL, "Boîte aux lettres, aucune PR"],
    [
      "open",
      rejouer(livraison({ arret: "conflit résolu, PR à relire" })),
      "Boîte aux lettres, PR #42 ouverte",
    ],
    [
      "waiting on the CI",
      rejouer(livraison()),
      "Boîte aux lettres, PR #42 CI en attente",
    ],
    [
      "merged",
      rejouer(livraison(), ev("ci_merge_done", { merged: true })),
      "Boîte aux lettres, PR #42 mergée",
    ],
    [
      "refused",
      rejouer(livraison(), ev("ci_merge_done", { merged: false })),
      "Boîte aux lettres, PR #42 refusée",
    ],
  ];

  it.each(CAS)(
    "renders the %s state with its own aria-label",
    async (_nom, etat, libelle) => {
      vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);

      render(<BoiteAuxLettres projet="ide-core" etat={etat} />);
      await act(async () => {});

      expect(screen.getByRole("group", { name: libelle })).toBeInTheDocument();
    },
  );

  it("puts the short label in a tooltip, not under the box, for a room without a pull request", async () => {
    vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);

    render(<BoiteAuxLettres projet="ide-core" etat={INITIAL} />);
    await act(async () => {});

    expect(screen.queryByText("aucune PR")).toBeNull();
    act(() => screen.getByRole("group").focus());
    expect(screen.getByRole("tooltip")).toHaveTextContent("aucune PR");
    expect(screen.queryByText(/Boîte aux lettres/)).toBeNull();
  });

  it("writes nothing beside the box and gives the pull request in the tooltip", async () => {
    vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);

    render(
      <BoiteAuxLettres
        projet="ide-core"
        etat={rejouer(livraison({ arret: "conflit résolu, PR à relire" }))}
      />,
    );
    await act(async () => {});

    expect(screen.queryByText("#42")).toBeNull();
    act(() => screen.getByRole("group").focus());
    expect(screen.getByRole("tooltip")).toHaveTextContent("PR #42 ouverte");
  });

  it("uses five distinct labels", () => {
    expect(new Set(CAS.map(([, , libelle]) => libelle)).size).toBe(5);
  });

  it("rebuilds the state from pr-statuses when the run has no events left", async () => {
    const lire = vi
      .spyOn(api.github, "getPrStatuses")
      .mockResolvedValue([entree({ state: "merged" })]);

    render(<BoiteAuxLettres projet="ide-core" etat={etatAvecTicket()} />);

    await waitFor(() =>
      expect(
        screen.getByRole("button", {
          name: "Boîte aux lettres, PR #42 mergée",
        }),
      ).toBeInTheDocument(),
    );
    expect(lire).toHaveBeenCalledWith("ide-core");
  });

  it("maps a waiting CI, a closed and an open pull request after a reload", async () => {
    const lire = vi.spyOn(api.github, "getPrStatuses");

    lire.mockResolvedValue([entree({ state: "closed" })]);
    const { unmount } = render(
      <BoiteAuxLettres projet="ide-core" etat={etatAvecTicket()} />,
    );
    await screen.findByRole("button", {
      name: "Boîte aux lettres, PR #42 refusée",
    });
    unmount();
    _viderCacheResource();

    lire.mockResolvedValue([entree({ ci_status: "passing" })]);
    render(<BoiteAuxLettres projet="ide-core" etat={etatAvecTicket()} />);
    await screen.findByRole("button", {
      name: "Boîte aux lettres, PR #42 ouverte",
    });
  });

  it("opens the pull request when the box itself is clicked", async () => {
    vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([entree()]);
    const ouvrir = vi.spyOn(window, "open").mockImplementation(() => null);

    render(
      <BoiteAuxLettres
        projet="ide-core"
        etat={rejouer(ev("agent_started"), livraison())}
      />,
    );
    fireEvent.click(
      await screen.findByRole("button", { name: /Boîte aux lettres, PR #42/ }),
    );

    expect(ouvrir).toHaveBeenCalledWith(
      "https://example.test/org/repo/pull/42",
      "_blank",
      "noopener,noreferrer",
    );
  });

  it("keeps the box a plain group when pr-statuses does not know the pull request", async () => {
    const lire = vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);

    render(
      <BoiteAuxLettres
        projet="ide-core"
        etat={rejouer(ev("agent_started"), livraison())}
      />,
    );

    await waitFor(() => expect(lire).toHaveBeenCalled());
    expect(
      screen.getByRole("group", { name: /Boîte aux lettres, PR #42/ }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("opens the pull request from the project's repository when pr-statuses does not know it yet", async () => {
    vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
    vi.spyOn(api.projects, "list").mockResolvedValue([
      {
        id: "ide-core",
        name: "ide-core",
        path: "/w/ide-core",
        description: "",
        active_agents: [],
        stack: null,
        raw_claude_md: "",
        github_remote: "owner/repo",
      },
    ]);
    const ouvrir = vi.spyOn(window, "open").mockImplementation(() => null);

    render(
      <BoiteAuxLettres
        projet="ide-core"
        etat={rejouer(ev("agent_started"), livraison())}
      />,
    );
    fireEvent.click(
      await screen.findByRole("button", { name: /Boîte aux lettres, PR #42/ }),
    );

    expect(ouvrir).toHaveBeenCalledWith(
      "https://github.com/owner/repo/pull/42",
      "_blank",
      "noopener,noreferrer",
    );
  });
});
