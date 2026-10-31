import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { usePolling } from "./usePolling";

function setVisibility(state: "visible" | "hidden"): void {
  Object.defineProperty(document, "visibilityState", {
    value: state,
    configurable: true,
  });
  document.dispatchEvent(new Event("visibilitychange"));
}

describe("usePolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setVisibility("visible");
  });
  afterEach(() => {
    setVisibility("visible");
    vi.useRealTimers();
  });

  it("calls back on every tick and not before", () => {
    const rappel = vi.fn();
    renderHook(() => usePolling(rappel, { cadenceMs: 1_000 }));

    expect(rappel).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(3_000);
    });
    expect(rappel).toHaveBeenCalledTimes(3);
  });

  it("calls back at once when asked to, and again on relance", () => {
    const rappel = vi.fn();
    const { rerender } = renderHook(
      ({ relance }: { relance: string }) =>
        usePolling(rappel, { cadenceMs: 1_000, immediat: true, relance }),
      { initialProps: { relance: "a" } },
    );
    expect(rappel).toHaveBeenCalledTimes(1);

    rerender({ relance: "b" });
    expect(rappel).toHaveBeenCalledTimes(2);
  });

  it("does not tick while the window is hidden, and resumes when visible", () => {
    const rappel = vi.fn();
    renderHook(() => usePolling(rappel, { cadenceMs: 1_000 }));

    act(() => setVisibility("hidden"));
    act(() => {
      vi.advanceTimersByTime(5_000);
    });
    expect(rappel).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);

    act(() => setVisibility("visible"));
    act(() => {
      vi.advanceTimersByTime(2_000);
    });
    expect(rappel).toHaveBeenCalledTimes(2);
  });

  it("is suspended by a null cadence", () => {
    const rappel = vi.fn();
    renderHook(() => usePolling(rappel, { cadenceMs: null, immediat: true }));

    act(() => {
      vi.advanceTimersByTime(5_000);
    });
    expect(rappel).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("leaves no timer behind after unmount", () => {
    const rappel = vi.fn();
    const { unmount } = renderHook(() => usePolling(rappel, { cadenceMs: 1_000 }));
    expect(vi.getTimerCount()).toBe(1);

    unmount();
    act(() => {
      vi.advanceTimersByTime(5_000);
    });

    expect(vi.getTimerCount()).toBe(0);
    expect(rappel).not.toHaveBeenCalled();
  });

  it("calls the latest callback without restarting the timer", () => {
    const premier = vi.fn();
    const second = vi.fn();
    const { rerender } = renderHook(
      ({ rappel }: { rappel: () => void }) => usePolling(rappel, { cadenceMs: 1_000 }),
      { initialProps: { rappel: premier } },
    );

    act(() => {
      vi.advanceTimersByTime(500);
    });
    rerender({ rappel: second });
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(premier).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
  });
});
