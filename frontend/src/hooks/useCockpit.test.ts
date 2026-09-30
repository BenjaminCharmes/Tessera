import { describe, it, expect } from "vitest";
import { panelAfterProjectSwitch } from "./useCockpit";

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
