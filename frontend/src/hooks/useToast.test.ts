import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useToast } from "./useToast";

describe("useToast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts with empty toasts", () => {
    const { result } = renderHook(() => useToast());
    expect(result.current.toasts).toHaveLength(0);
  });

  it("addToast adds a toast with correct fields", () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.addToast("Hello", "success");
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe("Hello");
    expect(result.current.toasts[0].type).toBe("success");
  });

  it("removeToast removes by id", () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.addToast("Toast 1", "info");
      result.current.addToast("Toast 2", "error");
    });

    const id = result.current.toasts[0].id;
    act(() => {
      result.current.removeToast(id);
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe("Toast 2");
  });

  it("auto-dismisses after default 3000ms", async () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.addToast("Auto dismiss", "success");
    });
    expect(result.current.toasts).toHaveLength(1);

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(result.current.toasts).toHaveLength(0);
  });

  it("respects custom duration", async () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.addToast("Short", "info", 1000);
    });

    await act(async () => {
      vi.advanceTimersByTime(999);
    });
    expect(result.current.toasts).toHaveLength(1);

    await act(async () => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current.toasts).toHaveLength(0);
  });

  it("stacks multiple toasts", () => {
    const { result } = renderHook(() => useToast());

    act(() => {
      result.current.addToast("First", "success");
      result.current.addToast("Second", "error");
      result.current.addToast("Third", "info");
    });

    expect(result.current.toasts).toHaveLength(3);
  });
});
