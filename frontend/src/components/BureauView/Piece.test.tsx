import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { INITIAL } from "../../hooks/streamState";
import { api } from "../../lib/api";
import Piece from "./Piece";
import { DERNIER, T0, etatApresPipeline, etatEnCodage, etatEnSecurite } from "./etatsDeTest";

function bulle(): string | null {
  return screen.queryByTestId("bulle")?.textContent ?? null;
}

function pastille(): string | null {
  const section = screen.getByRole("region", { name: "ide-core" });
  return section.querySelector("[data-etat]")?.textContent ?? null;
}

beforeEach(() => {
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

/** Les boutons des cinq postes : l'interrupteur et la porte de la pièce n'en sont pas. */
function boutonsDesPostes(): HTMLElement[] {
  return screen.getAllByRole("button").filter((b) => !/lumière/.test(b.getAttribute("aria-label") ?? ""));
}

describe("Piece", () => {
  it("renders five posts, one button each, named with their state", () => {
    render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    const boutons = boutonsDesPostes();
    expect(boutons.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Codeur, a fini",
      "Testeur, a fini",
      "Sécurité, travaille",
      "Reviewer, attend son tour",
      "Validateur, attend son tour",
    ]);
  });

  it("names a busy, a done and a free post", () => {
    render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    expect(screen.getByRole("button", { name: "Sécurité, travaille" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Codeur, a fini" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reviewer, attend son tour" })).toBeInTheDocument();
  });

  it("draws a pill and no bubble for a busy post that works", () => {
    render(<Piece projet="ide-core" etat={etatEnCodage()} maintenant={T0 + 5_000} />);

    expect(screen.queryByTestId("bulle")).toBeNull();
    expect(pastille()).toBe("travaille");
  });

  it("gives no post a pointer cursor when nothing listens to the choice", () => {
    render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    for (const bouton of boutonsDesPostes()) {
      expect(bouton.className).not.toContain("cursor-pointer");
    }
  });

  it("makes only the busy post clickable when a choice is listened to", () => {
    const onChoisir = vi.fn();
    render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} onChoisir={onChoisir} />);

    for (const nom of ["Codeur, a fini", "Testeur, a fini", "Reviewer, attend son tour", "Validateur, attend son tour"]) {
      const bouton = screen.getByRole("button", { name: nom });
      fireEvent.click(bouton);
      expect(bouton.className).not.toContain("cursor-pointer");
    }
    expect(onChoisir).not.toHaveBeenCalled();

    const occupe = screen.getByRole("button", { name: "Sécurité, travaille" });
    fireEvent.click(occupe);
    expect(occupe.className).toContain("cursor-pointer");
    expect(onChoisir).toHaveBeenCalledWith("ide-core", "securite");
  });

  it("draws neither bubble nor pill when no post is busy", () => {
    const etat = { ...etatEnCodage(), runClosed: true };
    render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 5_000} />);

    expect(screen.queryByTestId("bulle")).toBeNull();
    expect(within(screen.getByRole("region")).queryByText("travaille")).toBeNull();
  });

  it("outlines the room in amber when a question waits", () => {
    const etat = { ...etatEnCodage(), pendingQuestion: "On casse l'API ?" };
    render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 5_000} />);

    expect(screen.getByRole("region")).toHaveAttribute("data-contour", "amber");
  });
});

describe("Piece documentation and delivery", () => {
  it("says documentation after pipeline_done then documentation_started, in blue", () => {
    render(<Piece projet="ide-core" etat={etatApresPipeline(["documentation_started"])} maintenant={T0} />);

    expect(pastille()).toBe("documentation");
    expect(screen.getByText("documentation")).toHaveAttribute("data-etat", "en-cours");
  });

  it("says the delivery steps after livraison_started", () => {
    render(
      <Piece
        projet="ide-core"
        etat={etatApresPipeline(["documentation_started", "livraison_started"])}
        maintenant={T0}
      />,
    );

    expect(pastille()).toBe("livraison : rebase, tests, PR");
    expect(screen.queryByText("documentation")).toBeNull();
  });

  it("says neither once the run is closed", () => {
    const etat = etatApresPipeline(["documentation_started", "livraison_started", "run_closed"]);
    render(<Piece projet="ide-core" etat={etat} maintenant={T0} />);

    expect(pastille()).toBeNull();
    expect(screen.queryByText(/documentation|livraison/)).toBeNull();
  });
});

/** Le sprite `personnage` d'un poste, repéré par le nom accessible du bouton. */
function personnagesDuPoste(nom: string): Element[] {
  const bouton = screen.getByRole("button", { name: nom });
  return [...bouton.querySelectorAll('[data-sprite="personnage"]')];
}

describe("Piece furniture", () => {
  it("lays a plank floor and a plant in each work room", () => {
    render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0} />);

    const piece = screen.getByRole("region", { name: "ide-core" });
    expect(piece.querySelector('[data-sol="lames"]')).not.toBeNull();
    expect(piece.querySelectorAll('[data-sprite="plante"]')).toHaveLength(1);
  });

  it("keeps the plant in a room whose run is on", () => {
    render(<Piece projet="ide-core" etat={etatEnCodage()} maintenant={T0 + 5_000} />);

    const piece = screen.getByRole("region", { name: "ide-core" });
    expect(piece.querySelectorAll('[data-sprite="plante"]')).toHaveLength(1);
  });

  it("writes the empty mailbox label in the bottom bar", async () => {
    render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0} />);

    expect(await screen.findByText("aucune PR")).toBeInTheDocument();
  });
});

describe("Piece characters", () => {
  it("seats a character, still and without animation, at a post that waits its turn", () => {
    render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    const [personnage, ...autres] = personnagesDuPoste("Reviewer, attend son tour");

    expect(autres).toEqual([]);
    expect(personnage).toHaveAttribute("data-pose", "assis");
    expect(personnage?.querySelector(".anim-tape")).toBeNull();
    expect(screen.getAllByRole("button", { name: /attend son tour/ })).toHaveLength(2);
  });

  it("stands a character out of a post that is done, and keeps its tick on the screen", () => {
    const { container } = render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    const bouton = screen.getByRole("button", { name: "Codeur, a fini" });
    const agent = container.querySelector('[data-agent="codeur"]');

    expect(agent?.querySelectorAll('[data-sprite="personnage"]')).toHaveLength(1);
    expect(agent?.querySelector('[data-pose="debout"]')).not.toBeNull();
    expect(agent?.querySelector(".anim-tape")).toBeNull();
    expect(bouton.querySelector('[data-sprite="personnage"]')).toBeNull();
    expect(bouton.querySelector('[data-sprite="coche"]')).not.toBeNull();
  });

  it("keeps the busy character seated and typing", () => {
    render(<Piece projet="ide-core" etat={etatEnCodage()} maintenant={T0 + 5_000} />);

    const [personnage] = personnagesDuPoste("Codeur, travaille");

    expect(personnage).toHaveAttribute("data-pose", "assis");
    expect(personnage?.querySelector(".anim-tape")).not.toBeNull();
  });

  it("draws no character in a room without run", () => {
    const { container } = render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0} />);

    expect(container.querySelectorAll('[data-sprite="personnage"]')).toHaveLength(0);
    expect(container.querySelectorAll('[data-sprite="coche"]')).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Codeur, libre" })).toBeInTheDocument();
  });

  it("draws the standing character outside the desk grid of its post", () => {
    const { container } = render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    const bouton = screen.getByRole("button", { name: "Codeur, a fini" });
    const debout = container.querySelector('[data-agent="codeur"] [data-pose="debout"]');

    expect(debout).not.toBeNull();
    expect(bouton.contains(debout)).toBe(false);
    expect(debout?.closest("svg")?.getAttribute("viewBox")).toBe("0 0 12 20");
    expect(bouton.querySelector('[data-sprite="poste"]')?.getAttribute("viewBox")).toBe("0 0 16 18");
  });

  it("gives the same role a different look in two projects", () => {
    const etat = etatEnSecurite();
    const hasard = () => 0;
    const { container: a } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 5_000} hasard={hasard} />);
    const { container: b } = render(<Piece projet="kadoomi" etat={etat} maintenant={T0 + 5_000} hasard={hasard} />);
    const dessin = (c: HTMLElement) => c.querySelector('[data-pose="debout"]')?.innerHTML;

    expect(dessin(a)).toBeDefined();
    expect(dessin(a)).not.toBe(dessin(b));
  });

  it("keeps the same look from one render to the next", () => {
    const etat = etatEnSecurite();
    const hasard = () => 0;
    const { container: a } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 5_000} hasard={hasard} />);
    const { container: b } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 9_000} hasard={hasard} />);

    expect(a.querySelector('[data-pose="debout"]')?.innerHTML).toBe(
      b.querySelector('[data-pose="debout"]')?.innerHTML,
    );
  });

  it("spans the floor over the whole room, out of any horizontal scroll container", () => {
    const { container } = render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0} />);

    const sol = container.querySelector("section .sol-lames [data-etirement]");
    expect(sol).not.toBeNull();
    expect(sol?.className).toContain("w-full");
    expect(sol?.closest(".overflow-x-auto")).toBeNull();
  });

  it("stretches the abscissas to the room's width, keeping the sprites at their size", () => {
    vi.stubGlobal(
      "ResizeObserver",
      class {
        rappel: (e: { contentRect: { width: number } }[]) => void;
        constructor(rappel: (e: { contentRect: { width: number } }[]) => void) {
          this.rappel = rappel;
        }
        observe() {
          this.rappel([{ contentRect: { width: 1200 } }]);
        }
        disconnect() {}
      },
    );
    const { container } = render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0} />);
    vi.unstubAllGlobals();

    const sol = container.querySelector<HTMLElement>("[data-etirement]");
    expect(sol?.getAttribute("data-etirement")).toBe("1.5");
    expect(sol?.style.zoom ?? "").toBe("");
  });

  it("draws one character per post while a run is on", () => {
    const { container } = render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} />);

    expect(container.querySelectorAll('[data-sprite="personnage"]')).toHaveLength(5);
    expect(container.querySelectorAll('[data-pose="debout"]')).toHaveLength(2);
  });
});

describe("Piece health words", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(T0);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  const cas = [
    { depuis: 5, question: null, mot: "travaille", signe: null },
    { depuis: 31, question: null, mot: "silencieux", signe: "…" },
    { depuis: 181, question: null, mot: "figé ?", signe: "!" },
    // Une question : la bulle « ? » suit l'agent chez le directeur (ticket-597), la pièce garde la pastille.
    { depuis: 5, question: "On casse l'API ?", mot: "question", signe: null },
  ];

  it.each(cas)("shows $mot in the pill and $signe in the bubble at $depuis s", ({ depuis, question, mot, signe }) => {
    vi.setSystemTime(Date.parse(DERNIER) + depuis * 1000);
    render(
      <Piece
        projet="ide-core"
        etat={{ ...etatEnCodage(), pendingQuestion: question }}
        maintenant={Date.now()}
      />,
    );

    expect(bulle()).toBe(signe);
    expect(pastille()).toBe(mot);
    expect(screen.getByRole("button", { name: `Codeur, ${mot}` })).toBeInTheDocument();
  });
});
