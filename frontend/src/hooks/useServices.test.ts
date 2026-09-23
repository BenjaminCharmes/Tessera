import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { api } from "../lib/api";
import { useServices } from "./useServices";

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function service(over: Record<string, unknown> = {}) {
  return {
    nom: "api",
    project_id: "ide-core",
    pid: 4242,
    demarre_a: new Date().toISOString(),
    en_cours: true,
    code_de_sortie: null,
    ...over,
  };
}

describe("useServices", () => {
  it("ne demande rien tant qu'aucun projet n'est choisi", () => {
    const lister = vi.spyOn(api.services, "list");

    renderHook(() => useServices(null));

    expect(lister).not.toHaveBeenCalled();
  });

  it("liste les services du projet actif", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([service()]);

    const { result } = renderHook(() => useServices("ide-core"));

    await waitFor(() => expect(result.current.services).toHaveLength(1));
    expect(result.current.enCours).toBe(true);
  });

  it("démarre puis bascule sur « en cours »", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([]);
    const demarrer = vi
      .spyOn(api.services, "start")
      .mockResolvedValue({ services: [service()] });

    const { result } = renderHook(() => useServices("ide-core"));
    await waitFor(() => expect(result.current.services).toEqual([]));

    await act(async () => {
      await result.current.demarrer();
    });

    expect(demarrer).toHaveBeenCalledWith("ide-core");
    expect(result.current.enCours).toBe(true);
  });

  it("sait sans cliquer qu'un projet ne déclare rien", async () => {
    // Le défaut de ticket-146 : on ne l'apprenait qu'en échouant, et le
    // bouton disparaissait sous le curseur. La liste le dit dès le départ.
    vi.spyOn(api.services, "list").mockResolvedValue([]);
    const demarrer = vi.spyOn(api.services, "start");

    const { result } = renderHook(() => useServices("fluentdb"));

    await waitFor(() => expect(result.current.declare).toBe(false));
    expect(demarrer).not.toHaveBeenCalled();
  });

  it("garde le bouton en place quand le lancement échoue", async () => {
    // Un service déclaré mais qui refuse de démarrer doit laisser de quoi
    // réessayer, et dire pourquoi.
    vi.spyOn(api.services, "list").mockResolvedValue([
      service({ en_cours: false, pid: null }),
    ]);
    vi.spyOn(api.services, "start").mockRejectedValue(
      new Error("`cwd` sort du périmètre du projet"),
    );

    const { result } = renderHook(() => useServices("ide-core"));
    await waitFor(() => expect(result.current.declare).toBe(true));

    await act(async () => {
      await result.current.demarrer();
    });

    expect(result.current.declare).toBe(true);
    expect(result.current.erreur).toContain("périmètre");
  });

  it("signale un service mort de lui-même avec un code non nul", async () => {
    // C'est le cas où on va chercher les logs : il doit se voir, pas
    // disparaître en silence.
    vi.spyOn(api.services, "list").mockResolvedValue([
      service({ en_cours: false, code_de_sortie: 1 }),
    ]);

    const { result } = renderHook(() => useServices("ide-core"));

    await waitFor(() => expect(result.current.enEchec).toBe(true));
    expect(result.current.enCours).toBe(false);
  });

  it("arrête et vide la liste", async () => {
    const lister = vi
      .spyOn(api.services, "list")
      .mockResolvedValue([service()]);
    const arreter = vi
      .spyOn(api.services, "stop")
      .mockResolvedValue({ arretes: 1 });

    const { result } = renderHook(() => useServices("ide-core"));
    await waitFor(() => expect(result.current.services).toHaveLength(1));

    lister.mockResolvedValue([]);
    await act(async () => {
      await result.current.arreter();
    });

    expect(arreter).toHaveBeenCalledWith("ide-core");
    expect(result.current.enCours).toBe(false);
  });
});
