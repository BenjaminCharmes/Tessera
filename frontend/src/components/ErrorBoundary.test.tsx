import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ErrorBoundary from "./ErrorBoundary";

function ThrowOnRender({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error("test render error");
  return <div>content</div>;
}

let mutableShouldThrow = true;
function ThrowOnRenderMutable() {
  if (mutableShouldThrow) throw new Error("mutable render error");
  return <div>recovered</div>;
}

// Suppress console.error from intentional throws in tests
beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});

describe("ErrorBoundary", () => {
  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <ThrowOnRender shouldThrow={false} />
      </ErrorBoundary>,
    );
    expect(screen.getByText("content")).toBeInTheDocument();
  });

  it("renders default fallback when child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowOnRender shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/inattendue/i)).toBeInTheDocument();
    expect(screen.getByText("test render error")).toBeInTheDocument();
  });

  it("renders custom fallback when provided", () => {
    render(
      <ErrorBoundary fallback={<div>custom fallback</div>}>
        <ThrowOnRender shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(screen.getByText("custom fallback")).toBeInTheDocument();
  });

  it("recovers when Réessayer is clicked", async () => {
    mutableShouldThrow = true;
    render(
      <ErrorBoundary>
        <ThrowOnRenderMutable />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/inattendue/i)).toBeInTheDocument();

    // Disable throw before clicking so the reset re-render succeeds
    mutableShouldThrow = false;
    await userEvent.click(screen.getByText("Réessayer"));

    expect(screen.getByText("recovered")).toBeInTheDocument();
  });
});
