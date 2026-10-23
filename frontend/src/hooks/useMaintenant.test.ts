import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useMaintenant } from "./useMaintenant";

describe("useMaintenant", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-23T10:00:00.000Z"));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("advances with the interval", () => {
    const { result } = renderHook(() => useMaintenant(1_000));
    const debut = result.current;

    act(() => {
      vi.advanceTimersByTime(3_000);
    });

    expect(result.current - debut).toBe(3_000);
  });

  it("stops ticking after unmount", () => {
    const { unmount } = renderHook(() => useMaintenant(1_000));

    unmount();

    expect(vi.getTimerCount()).toBe(0);
  });
});
