import { describe, expect, it } from "vitest";
import type { PRStatus } from "../../types/api";
import { boiteDepuisPr } from "./boiteDepuisPr";
import { libelleDeLaBoite } from "./libelleDeLaBoite";

function pr(over: Partial<PRStatus>): PRStatus {
  return { state: "open", ci_status: "none", pr_url: "https://example.test/pull/7", pr_number: 7, ...over };
}

describe("boiteDepuisPr", () => {
  it("is empty without a pull request", () => {
    expect(boiteDepuisPr(null)).toEqual({ etat: "aucune", pr: null });
    expect(boiteDepuisPr(undefined)).toEqual({ etat: "aucune", pr: null });
  });

  it("maps a merged pull request to mergee", () => {
    expect(boiteDepuisPr(pr({ state: "merged" }))).toEqual({ etat: "mergee", pr: 7 });
  });

  it("maps a closed pull request to refusee", () => {
    expect(boiteDepuisPr(pr({ state: "closed" }))).toEqual({ etat: "refusee", pr: 7 });
  });

  it("maps an open pull request with a pending CI to ci", () => {
    expect(boiteDepuisPr(pr({ ci_status: "pending" }))).toEqual({ etat: "ci", pr: 7 });
  });

  it.each(["passing", "failing", "none", "unreadable"] as const)(
    "maps an open pull request with a %s CI to ouverte",
    (ci) => {
      expect(boiteDepuisPr(pr({ ci_status: ci }))).toEqual({ etat: "ouverte", pr: 7 });
    },
  );
});

describe("libelleDeLaBoite", () => {
  it("says each state in words", () => {
    expect(libelleDeLaBoite({ etat: "aucune", pr: null })).toBe("Boîte aux lettres, aucune PR");
    expect(libelleDeLaBoite({ etat: "ci", pr: 7 })).toBe("Boîte aux lettres, PR #7 CI en attente");
  });
});
