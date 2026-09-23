import { describe, it, expect } from "vitest";
import { adresseDansLaSortie } from "./adresse";

describe("adresseDansLaSortie", () => {
  it("trouve l'adresse que Vite annonce", () => {
    expect(
      adresseDansLaSortie(["  ➜  Local:   http://localhost:5174/"]),
    ).toBe("http://localhost:5174/");
  });

  it("trouve celle d'uvicorn", () => {
    expect(
      adresseDansLaSortie(["INFO: Uvicorn running on http://127.0.0.1:8000"]),
    ).toBe("http://127.0.0.1:8000");
  });

  it("retient la derniere : un serveur qui redemarre change de port", () => {
    expect(
      adresseDansLaSortie([
        "Local: http://localhost:5173/",
        "Port 5173 is in use, trying another one...",
        "Local: http://localhost:5174/",
      ]),
    ).toBe("http://localhost:5174/");
  });

  it("ne rend rien plutot qu'un lien mort", () => {
    // Mieux vaut aucun lien qu'un lien qui ne mene nulle part.
    expect(adresseDansLaSortie([])).toBeNull();
    expect(adresseDansLaSortie(["compilation terminee"])).toBeNull();
    expect(adresseDansLaSortie(["voir https://exemple.com/doc"])).toBeNull();
  });

  it("coupe la ponctuation collee a l'URL", () => {
    expect(adresseDansLaSortie(["ouvre http://localhost:3000."])).toBe(
      "http://localhost:3000",
    );
  });
});
