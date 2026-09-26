import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { parmi, useEtatPersistant } from "./useEtatPersistant";

describe("useEtatPersistant", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("relit la valeur apres un remontage", () => {
    // Un rechargement retombait sur le panneau par defaut : c'est le clic
    // qu'on veut economiser (ticket-193).
    const premier = renderHook(() => useEtatPersistant("panneau", "projects"));
    act(() => premier.result.current[1]("tickets"));
    premier.unmount();

    const second = renderHook(() => useEtatPersistant("panneau", "projects"));
    expect(second.result.current[0]).toBe("tickets");
  });

  it("ecarte une valeur memorisee qui ne passe pas le garde", () => {
    window.localStorage.setItem("tessera.ui.panneau", JSON.stringify("disparu"));

    const { result } = renderHook(() =>
      useEtatPersistant("panneau", "projects", parmi(["projects", "tickets"])),
    );
    expect(result.current[0]).toBe("projects");
  });

  it("sert le defaut quand le stockage leve, sans casser le rendu", () => {
    const getItem = vi
      .spyOn(Storage.prototype, "getItem")
      .mockImplementation(() => {
        throw new Error("bloque");
      });
    const setItem = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("bloque");
      });
    try {
      const { result } = renderHook(() => useEtatPersistant("cle", 3));
      expect(result.current[0]).toBe(3);
      act(() => result.current[1](4));
      expect(result.current[0]).toBe(4);
    } finally {
      getItem.mockRestore();
      setItem.mockRestore();
    }
  });
});
