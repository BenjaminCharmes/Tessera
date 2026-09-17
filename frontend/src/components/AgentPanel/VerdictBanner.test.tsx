import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import VerdictBanner from "./VerdictBanner";

describe("VerdictBanner", () => {
  it("shows APPROVED banner for approved content", () => {
    render(<VerdictBanner content={"APPROVED\nLooks good, ship it!"} />);
    expect(screen.getByText(/APPROVED/)).toBeInTheDocument();
    expect(screen.getByText("Looks good, ship it!")).toBeInTheDocument();
  });

  it("shows CHANGES_REQUESTED banner when keyword is present", () => {
    render(
      <VerdictBanner content={"CHANGES_REQUESTED\nPlease fix the types."} />,
    );
    expect(screen.getByText(/CHANGES_REQUESTED/)).toBeInTheDocument();
    expect(screen.getByText("Please fix the types.")).toBeInTheDocument();
  });

  it("shows CHANGES_REQUESTED when both keywords appear (CHANGES_REQUESTED takes priority)", () => {
    render(
      <VerdictBanner content={"CHANGES_REQUESTED (not APPROVED)\nFix it."} />,
    );
    expect(screen.getByText(/CHANGES_REQUESTED/)).toBeInTheDocument();
  });

  it("shows CHANGES_REQUESTED when no keyword matches", () => {
    render(<VerdictBanner content={"The code needs work."} />);
    expect(screen.getByText(/CHANGES_REQUESTED/)).toBeInTheDocument();
  });

  it("renders without summary when content is only the keyword", () => {
    render(<VerdictBanner content={"APPROVED"} />);
    expect(screen.getByText(/APPROVED/)).toBeInTheDocument();
  });
});
