import { beforeEach, describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useFiltresTickets } from "./useFiltresTickets";
import { FILTRES_VIDES } from "../lib/filtresTickets";

describe("useFiltresTickets", () => {
  beforeEach(() => window.localStorage.clear());

  it("part des filtres vides", () => {
    const { result } = renderHook(() => useFiltresTickets("p"));
    expect(result.current.filtres).toEqual(FILTRES_VIDES);
  });

  it("survit a un remontage, projet par projet", () => {
    const premier = renderHook(() => useFiltresTickets("p"));
    act(() => premier.result.current.setFiltres({ ...FILTRES_VIDES, texte: "carte" }));
    premier.unmount();

    const second = renderHook(() => useFiltresTickets("p"));
    expect(second.result.current.filtres.texte).toBe("carte");

    const autre = renderHook(() => useFiltresTickets("q"));
    expect(autre.result.current.filtres.texte).toBe("");
  });
});
