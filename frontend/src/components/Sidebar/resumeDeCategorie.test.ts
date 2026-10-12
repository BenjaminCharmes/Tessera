import { describe, expect, it } from "vitest";
import { resumeDeCategorie } from "./resumeDeCategorie";
import type { Project } from "../../types/api";

function projet(name: string): Project {
  return {
    id: name,
    name,
    path: `/w/${name}`,
    description: "",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
  };
}

describe("resumeDeCategorie", () => {
  it("names the projects with a plural count", () => {
    expect(resumeDeCategorie([projet("a"), projet("b")])).toBe("2 projets : a, b");
  });

  it("uses the singular for one project", () => {
    expect(resumeDeCategorie([projet("a")])).toBe("1 projet : a");
  });
});
