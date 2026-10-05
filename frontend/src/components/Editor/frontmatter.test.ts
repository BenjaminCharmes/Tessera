import { describe, expect, it } from "vitest";
import { separerFrontmatter } from "./frontmatter";

describe("separerFrontmatter — ticket-334", () => {
  it("splits the YAML header from the body, one field per key", () => {
    const { champs, corps } = separerFrontmatter(
      '---\nid: ticket-042\ntitle: "Un titre"\ndepends_on: []\n---\n\n# ticket-042\n',
    );

    expect(champs).toEqual([
      ["id", "ticket-042"],
      ["title", "Un titre"],
      ["depends_on", "[]"],
    ]);
    expect(corps).toBe("\n# ticket-042\n");
  });

  it("joins a value folded over several lines, and reads CRLF files", () => {
    // Le titre du ticket-327 est replié sur deux lignes par le sérialiseur YAML.
    const { champs } = separerFrontmatter(
      "---\r\ntitle: A finished run is reopened,\r\n  and the stats view loads fast\r\ntype: feat\r\n---\r\nCorps",
    );

    expect(champs).toEqual([
      ["title", "A finished run is reopened, and the stats view loads fast"],
      ["type", "feat"],
    ]);
  });

  it("leaves a file without a header untouched", () => {
    const source = "# Titre\n\n---\n\nUne règle horizontale, pas un en-tête.\n";

    expect(separerFrontmatter(source)).toEqual({ champs: null, corps: source });
  });
});
