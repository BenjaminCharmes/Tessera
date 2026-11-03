import { describe, it, expect } from "vitest";
import { validateGithubUrl, validateLocalPath } from "./importValidation";

describe("validateLocalPath", () => {
  it("rejects an empty or blank path", () => {
    expect(validateLocalPath("")).toBe("Le chemin est requis");
    expect(validateLocalPath("   ")).toBe("Le chemin est requis");
  });

  it("accepts a non-empty path", () => {
    expect(validateLocalPath("/ws/mon-projet")).toBeNull();
  });
});

describe("validateGithubUrl", () => {
  it("rejects an empty URL", () => {
    expect(validateGithubUrl(" ")).toBe("L'URL est requise");
  });

  it("rejects a URL that is not a GitHub repository", () => {
    expect(validateGithubUrl("https://example.com/a/b")).toContain(
      "Format invalide",
    );
    expect(validateGithubUrl("https://github.com/owner")).toContain(
      "Format invalide",
    );
  });

  it("accepts a repository URL, ignoring surrounding spaces", () => {
    expect(validateGithubUrl(" https://github.com/owner/mon-repo ")).toBeNull();
  });
});
