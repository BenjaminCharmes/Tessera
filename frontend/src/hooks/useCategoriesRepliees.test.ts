import { beforeEach, describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useCategoriesRepliees } from "./useCategoriesRepliees";

describe("useCategoriesRepliees", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("bascule une catégorie puis la rend", () => {
    const { result } = renderHook(() => useCategoriesRepliees());
    expect(result.current.estRepliee("jeux")).toBe(false);

    act(() => result.current.basculer("jeux"));
    expect(result.current.estRepliee("jeux")).toBe(true);

    act(() => result.current.basculer("jeux"));
    expect(result.current.estRepliee("jeux")).toBe(false);
  });

  it("distingue les projets sans catégorie d'une catégorie nommée", () => {
    const { result } = renderHook(() => useCategoriesRepliees());

    act(() => result.current.basculer(null));

    expect(result.current.estRepliee(null)).toBe(true);
    expect(result.current.estRepliee("jeux")).toBe(false);
  });

  it("prévient les autres vues montées quand l'une écrit", () => {
    const sidebar = renderHook(() => useCategoriesRepliees());
    const vue = renderHook(() => useCategoriesRepliees());

    act(() => sidebar.result.current.basculer("jeux"));

    expect(vue.result.current.estRepliee("jeux")).toBe(true);
  });
});
