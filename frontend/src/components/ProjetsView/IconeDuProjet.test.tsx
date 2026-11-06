import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { oublierJeton, saisirJeton } from "../../lib/auth";
import IconeDuProjet from "./IconeDuProjet";

const AVEC_ICONE = { id: "serpent", name: "Serpent", icon: true };
const originaux = { creer: URL.createObjectURL, revoquer: URL.revokeObjectURL };
let fetchSimule: ReturnType<typeof vi.fn<typeof fetch>>;
let revoquer: ReturnType<typeof vi.fn<(url: string) => void>>;

beforeEach(() => {
  saisirJeton("secret-de-test");
  fetchSimule = vi.fn<typeof fetch>(async () => new Response(new Uint8Array([137, 80, 78, 71])));
  vi.stubGlobal("fetch", fetchSimule);
  revoquer = vi.fn<(url: string) => void>();
  URL.createObjectURL = vi.fn(() => "blob:http://localhost/icone");
  URL.revokeObjectURL = revoquer;
});

afterEach(() => {
  oublierJeton();
  vi.unstubAllGlobals();
  URL.createObjectURL = originaux.creer;
  URL.revokeObjectURL = originaux.revoquer;
});

describe("IconeDuProjet with a session token", () => {
  it("fetches the icon with the Authorization header and never puts the token in a src", async () => {
    const { container } = render(<IconeDuProjet projet={AVEC_ICONE} />);

    await waitFor(() => expect(container.querySelector("img")).not.toBeNull());
    const [adresse, init] = fetchSimule.mock.calls[0] ?? [];
    expect(String(adresse)).toBe("/api/v1/projects/serpent/icon");
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer secret-de-test");
    for (const img of container.querySelectorAll("img")) {
      expect(img.getAttribute("src")).toBe("blob:http://localhost/icone");
      expect(img.getAttribute("src")).not.toContain("token=");
    }
  });

  it("shows the initial while the icon loads, then falls back to it when the request fails", async () => {
    fetchSimule.mockResolvedValue(new Response("non", { status: 401 }));
    const { container } = render(<IconeDuProjet projet={AVEC_ICONE} />);

    expect(screen.getByTestId("icone-initiale")).toHaveTextContent("S");
    await waitFor(() => expect(fetchSimule).toHaveBeenCalled());
    expect(container.querySelector("img")).toBeNull();
  });

  it("revokes the object URL when it unmounts", async () => {
    const { container, unmount } = render(<IconeDuProjet projet={AVEC_ICONE} />);
    await waitFor(() => expect(container.querySelector("img")).not.toBeNull());
    expect(revoquer).not.toHaveBeenCalled();

    unmount();
    expect(revoquer).toHaveBeenCalledWith("blob:http://localhost/icone");
  });

  it("does not request anything for a project without icon", () => {
    render(<IconeDuProjet projet={{ ...AVEC_ICONE, icon: false }} />);
    expect(fetchSimule).not.toHaveBeenCalled();
    expect(screen.getByTestId("icone-initiale")).toBeInTheDocument();
  });
});
