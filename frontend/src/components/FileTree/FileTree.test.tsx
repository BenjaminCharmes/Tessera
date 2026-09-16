import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FileTree from "./index";

vi.mock("../../lib/fs");

import * as fs from "../../lib/fs";
const liste = vi.mocked(fs.listEntries);

describe("FileTree", () => {
  beforeEach(() => {
    liste.mockReset();
  });

  it("liste le contenu de la racine du projet", async () => {
    liste.mockResolvedValue([
      { name: "src", path: "/p/src", is_dir: true },
      { name: "README.md", path: "/p/README.md", is_dir: false },
    ]);

    render(<FileTree racine="/p" onSelectFile={() => {}} />);

    expect(await screen.findByText("src")).toBeInTheDocument();
    expect(screen.getByText("README.md")).toBeInTheDocument();
  });

  it("ne charge un dossier qu'a son ouverture", async () => {
    // Un depot client peut contenir des dizaines de milliers de fichiers :
    // tout charger d'un coup fige l'interface pour rien.
    liste.mockResolvedValueOnce([{ name: "src", path: "/p/src", is_dir: true }]);
    liste.mockResolvedValueOnce([
      { name: "app.ts", path: "/p/src/app.ts", is_dir: false },
    ]);

    render(<FileTree racine="/p" onSelectFile={() => {}} />);
    await screen.findByText("src");
    expect(liste).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByText("src"));

    expect(await screen.findByText("app.ts")).toBeInTheDocument();
    expect(liste).toHaveBeenCalledWith("/p/src");
  });

  it("remonte le fichier choisi", async () => {
    const onSelectFile = vi.fn();
    liste.mockResolvedValue([
      { name: "README.md", path: "/p/README.md", is_dir: false },
    ]);

    render(<FileTree racine="/p" onSelectFile={onSelectFile} />);
    await userEvent.click(await screen.findByText("README.md"));

    expect(onSelectFile).toHaveBeenCalledWith("/p/README.md");
  });

  it("affiche l'erreur plutot que de rester vide", async () => {
    liste.mockRejectedValue(new Error("403"));

    render(<FileTree racine="/p" onSelectFile={() => {}} />);

    expect(await screen.findByText(/Impossible de lire/i)).toBeInTheDocument();
  });
});
