import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import GroupeSuperviseur from "./GroupeSuperviseur";
import RecapSuperviseur from "./RecapSuperviseur";
import { lireLeRecap } from "../../lib/apiSupervision";
import { CLE_DERNIERE_VISITE } from "../../lib/bureau/derniereVisite";
import type { RecapSupervision } from "../../types/supervision";

vi.mock("../../lib/apiSupervision", () => ({ lireLeRecap: vi.fn() }));

function recap(over: Partial<RecapSupervision> = {}): RecapSupervision {
  return { depuis: null, lignes: [], a_toi: [], ...over };
}

describe("RecapSuperviseur", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(lireLeRecap).mockReset();
  });

  it("lists the journal lines from the remembered date", async () => {
    window.localStorage.setItem(CLE_DERNIERE_VISITE, "2026-11-03");
    vi.mocked(lireLeRecap).mockResolvedValue(
      recap({
        depuis: "2026-11-03",
        lignes: [
          { jour: "2026-11-05", action: "accepter-regle", cible: "ticket-12", sha: "abcdef0123456789", resume: "règle acceptée" },
          { jour: "2026-11-04", action: "relancer-file", cible: "file-1", sha: "1234567890abcdef", resume: "" },
        ],
      }),
    );

    render(<RecapSuperviseur onFermer={vi.fn()} />);

    expect(await screen.findByText(/accepter-regle/)).toBeInTheDocument();
    expect(lireLeRecap).toHaveBeenCalledWith("2026-11-03");
    expect(screen.getByText("Depuis le 2026-11-03")).toBeInTheDocument();
    expect(screen.getByText(/ticket-12/)).toBeInTheDocument();
    expect(screen.getByText(/abcdef0 · règle acceptée/)).toBeInTheDocument();
    expect(screen.getByText(/relancer-file/)).toBeInTheDocument();
  });

  it("asks for the whole journal when no visit is remembered", async () => {
    vi.mocked(lireLeRecap).mockResolvedValue(recap());

    render(<RecapSuperviseur onFermer={vi.fn()} />);

    await screen.findByText(/Rien à signaler/);
    expect(lireLeRecap).toHaveBeenCalledWith(null);
    expect(screen.getByText("Depuis le début")).toBeInTheDocument();
  });

  it("says there is nothing for an empty recap, without an error", async () => {
    vi.mocked(lireLeRecap).mockResolvedValue(recap());

    render(<RecapSuperviseur onFermer={vi.fn()} />);

    expect(await screen.findByText(/Rien à signaler/)).toBeInTheDocument();
    expect(screen.queryByText(/n'a pas pu être lu/)).not.toBeInTheDocument();
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });

  it("says so when the journal cannot be read", async () => {
    vi.mocked(lireLeRecap).mockRejectedValue(new Error("503"));

    render(<RecapSuperviseur onFermer={vi.fn()} />);

    expect(await screen.findByText("Le journal n'a pas pu être lu.")).toBeInTheDocument();
  });

  it("remembers today as the last visit on close, and offers no action button", async () => {
    vi.mocked(lireLeRecap).mockResolvedValue(recap());
    const onFermer = vi.fn();
    render(<RecapSuperviseur onFermer={onFermer} />);
    await screen.findByText(/Rien à signaler/);

    expect(screen.getAllByRole("button").map((b) => b.textContent)).toEqual(["Fermer"]);
    fireEvent.click(screen.getByRole("button", { name: "Fermer" }));

    expect(onFermer).toHaveBeenCalledTimes(1);
    expect(window.localStorage.getItem(CLE_DERNIERE_VISITE)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("ignores an unreadable remembered date", async () => {
    window.localStorage.setItem(CLE_DERNIERE_VISITE, "hier");
    vi.mocked(lireLeRecap).mockResolvedValue(recap());

    render(<RecapSuperviseur onFermer={vi.fn()} />);

    await waitFor(() => expect(lireLeRecap).toHaveBeenCalledWith(null));
  });
});

describe("GroupeSuperviseur", () => {
  it("opens the recap from the column and closes it again", async () => {
    vi.mocked(lireLeRecap).mockResolvedValue(recap());
    render(<GroupeSuperviseur cas={[]} />);

    fireEvent.click(screen.getByRole("button", { name: "Récap du superviseur" }));
    expect(await screen.findByRole("region", { name: "Récap du superviseur" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Fermer" }));
    expect(screen.queryByRole("region", { name: "Récap du superviseur" })).not.toBeInTheDocument();
  });
});
