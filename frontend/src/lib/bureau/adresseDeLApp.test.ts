import { describe, expect, it } from "vitest";
import { adresseDeLApp } from "./adresseDeLApp";
import type { ServiceActif } from "../../types/api";

function service(over: Partial<ServiceActif> = {}): ServiceActif {
  return {
    nom: "front",
    project_id: "vigie",
    pid: 12,
    demarre_a: "2026-10-28T09:00:00Z",
    en_cours: true,
    code_de_sortie: null,
    ...over,
  };
}

describe("adresseDeLApp", () => {
  it("reads the local address a running service announced, colours removed", () => {
    const vite = service({
      sortie: [
        "  \u001b[32m➜\u001b[39m  Local:   \u001b[36mhttp://localhost:\u001b[1m5195\u001b[22m/\u001b[39m",
      ],
    });
    const uvicorn = service({
      sortie: [
        "INFO:     Uvicorn running on http://127.0.0.1:8025 (Press CTRL+C to quit)",
      ],
    });

    expect(adresseDeLApp([vite])).toBe("http://localhost:5195/");
    expect(adresseDeLApp([uvicorn])).toBe("http://127.0.0.1:8025");
  });

  it("gives nothing for a stopped service or an output without address", () => {
    expect(
      adresseDeLApp([
        service({ en_cours: false, sortie: ["http://localhost:5195/"] }),
      ]),
    ).toBeNull();
    expect(adresseDeLApp([service({ sortie: ["compiling…"] })])).toBeNull();
    expect(adresseDeLApp([])).toBeNull();
  });
});
