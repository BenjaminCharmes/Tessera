import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useFenetreVisible } from "./useFenetreVisible";

function setVisibility(state: "visible" | "hidden"): void {
  Object.defineProperty(document, "visibilityState", {
    value: state,
    configurable: true,
  });
}

afterEach(() => {
  // Restaurer l'état visible par défaut après chaque test.
  setVisibility("visible");
});

describe("useFenetreVisible", () => {
  it("returns true when document is visible", () => {
    setVisibility("visible");
    const { result } = renderHook(() => useFenetreVisible());
    expect(result.current).toBe(true);
  });

  it("returns false when document starts hidden", () => {
    setVisibility("hidden");
    const { result } = renderHook(() => useFenetreVisible());
    expect(result.current).toBe(false);
  });

  it("switches from true to false on visibilitychange", () => {
    setVisibility("visible");
    const { result } = renderHook(() => useFenetreVisible());
    expect(result.current).toBe(true);

    act(() => {
      setVisibility("hidden");
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(result.current).toBe(false);
  });

  it("switches from false to true on visibilitychange", () => {
    setVisibility("hidden");
    const { result } = renderHook(() => useFenetreVisible());
    expect(result.current).toBe(false);

    act(() => {
      setVisibility("visible");
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(result.current).toBe(true);
  });

  it("removes event listener on unmount", () => {
    setVisibility("visible");
    const removeEventListener = vi.spyOn(document, "removeEventListener");
    const { unmount } = renderHook(() => useFenetreVisible());
    unmount();
    expect(removeEventListener).toHaveBeenCalledWith(
      "visibilitychange",
      expect.any(Function),
    );
  });
});
