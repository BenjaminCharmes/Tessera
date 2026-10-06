import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import Editor from "./index";
import { readFile } from "../../lib/fs";

// Monaco charge un worker et un canvas : hors de portée de jsdom, et hors
// sujet ici — on vérifie quel contenu lui est passé.
vi.mock("@monaco-editor/react", () => ({
  default: ({ value }: { value: string }) => (
    <pre data-testid="monaco">{value}</pre>
  ),
}));

// lib/monaco exporte configureMonaco — on le stubbe pour éviter de charger
// les workers réels dans jsdom.
vi.mock("../../lib/monaco", () => ({ configureMonaco: vi.fn() }));

vi.mock("../../lib/fs", () => ({
  readFile: vi.fn(),
}));

/** Une promesse qu'on résout à la main, pour ordonner les réponses. */
function differee<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

beforeEach(() => {
  vi.mocked(readFile).mockReset();
});

describe("Editor", () => {
  it("affiche le fichier ouvert", async () => {
    vi.mocked(readFile).mockResolvedValue("print('a')");
    render(<Editor ticket={null} openFilePath="/w/a.py" />);

    expect(await screen.findByText("print('a')")).toBeInTheDocument();
    expect(screen.getByText("/w/a.py")).toBeInTheDocument();
  });

  it("ignore la lecture précédente quand elle aboutit après la suivante (ticket-123)", async () => {
    // Deux clics rapides dans l'arbre : la lecture du premier fichier, plus
    // lente, arrivait en dernier et remplaçait le contenu du second sous son
    // propre en-tête.
    const lente = differee<string>();
    const rapide = differee<string>();
    vi.mocked(readFile)
      .mockImplementationOnce(() => lente.promise)
      .mockImplementationOnce(() => rapide.promise);

    const { rerender } = render(<Editor ticket={null} openFilePath="/w/a.py" />);
    rerender(<Editor ticket={null} openFilePath="/w/b.py" />);

    await act(async () => {
      rapide.resolve("print('b')");
      await rapide.promise;
    });
    await act(async () => {
      lente.resolve("print('a')");
      await lente.promise;
    });

    expect(screen.getByTestId("monaco")).toHaveTextContent("print('b')");
    expect(screen.getByText("/w/b.py")).toBeInTheDocument();
  });

  it("signale une lecture impossible", async () => {
    vi.mocked(readFile).mockRejectedValue(new Error("ENOENT"));
    render(<Editor ticket={null} openFilePath="/w/absent.py" />);

    expect(
      await screen.findByText(/Impossible de lire le fichier/),
    ).toBeInTheDocument();
  });
});
