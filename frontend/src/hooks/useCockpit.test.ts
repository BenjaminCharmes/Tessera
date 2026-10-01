import { describe, it, expect } from "vitest";
import { panelAfterProjectSwitch, porteeEffectiveFor } from "./useCockpit";

// Acceptance criteria from ticket-271: switching project must preserve the
// active panel, except when coming from the projects list which opens tickets.
describe("panelAfterProjectSwitch", () => {
  it("keeps the usage panel when changing project", () => {
    expect(panelAfterProjectSwitch("usage")).toBe("usage");
  });

  it("keeps the chat panel when changing project", () => {
    expect(panelAfterProjectSwitch("chat")).toBe("chat");
  });

  it("switches to tickets when the projects panel is active", () => {
    expect(panelAfterProjectSwitch("projects")).toBe("tickets");
  });

  it("keeps every other panel unchanged", () => {
    expect(panelAfterProjectSwitch("tickets")).toBe("tickets");
    expect(panelAfterProjectSwitch("files")).toBe("files");
    expect(panelAfterProjectSwitch("history")).toBe("history");
    expect(panelAfterProjectSwitch("agents")).toBe("agents");
    expect(panelAfterProjectSwitch("supervision")).toBe("supervision");
  });
});

// Acceptance criteria from ticket-258: effective scope must be "tous" when no
// project is active, regardless of the user's prior selection.
describe("porteeEffectiveFor", () => {
  it("returns 'tous' when no project is active, ignoring prior selection", () => {
    expect(porteeEffectiveFor(null, "projet")).toBe("tous");
    expect(porteeEffectiveFor(null, "tous")).toBe("tous");
  });

  it("returns the user's choice when a project is active", () => {
    expect(porteeEffectiveFor({ id: "ide-core" }, "projet")).toBe("projet");
    expect(porteeEffectiveFor({ id: "ide-core" }, "tous")).toBe("tous");
  });
});
