import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CompteARebours from "./CompteARebours";

afterEach(() => {
  vi.useRealTimers();
});

describe("CompteARebours", () => {
  it("annonce le temps qui reste", () => {
    vi.useFakeTimers();
    vi.setSystemTime(Date.parse("2026-09-25T09:00:00Z"));

    render(<CompteARebours expireA="2026-09-25T09:02:00Z" />);

    expect(
      screen.getByText("Sans réponse, l'agent reprend dans 2m 0s."),
    ).toBeInTheDocument();
  });

  it("n'affiche rien sans échéance", () => {
    const { container } = render(<CompteARebours expireA={null} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("ne monte aucune horloge sans échéance", () => {
    // Une carte par run, un battement par seconde chacune : l'horloge ne
    // doit exister que lorsqu'elle affiche quelque chose.
    vi.useFakeTimers();

    render(<CompteARebours expireA={null} />);

    expect(vi.getTimerCount()).toBe(0);
  });
});
