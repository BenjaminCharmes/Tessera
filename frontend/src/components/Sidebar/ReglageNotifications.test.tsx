import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ReglageNotifications from "./ReglageNotifications";

describe("ReglageNotifications", () => {
  it("at actives state, explanation text is not displayed outside hover", () => {
    render(
      <ReglageNotifications active={true} etat="actives" onChange={() => {}} />,
    );

    expect(
      screen.queryByText(/quand un agent pose une question/i),
    ).not.toBeInTheDocument();
  });

  it("at actives state, explanation text appears on hover of the info icon", async () => {
    render(
      <ReglageNotifications active={true} etat="actives" onChange={() => {}} />,
    );

    await userEvent.hover(
      screen.getByRole("button", { name: /plus d'informations/i }),
    );

    expect(screen.getByRole("tooltip")).toHaveTextContent(
      /quand un agent pose une question/i,
    );
  });

  it("at bloquees state, blocked-by-browser text remains permanently visible", () => {
    render(
      <ReglageNotifications
        active={false}
        etat="bloquees"
        onChange={() => {}}
      />,
    );

    expect(screen.getByText(/bloquées par le navigateur/i)).toBeInTheDocument();
  });

  it("at coupees state, coupees text remains permanently visible", () => {
    render(
      <ReglageNotifications
        active={false}
        etat="coupees"
        onChange={() => {}}
      />,
    );

    expect(screen.getByText("coupées")).toBeInTheDocument();
  });

  it("at indisponibles state, checkbox is disabled", () => {
    render(
      <ReglageNotifications
        active={false}
        etat="indisponibles"
        onChange={() => {}}
      />,
    );

    expect(screen.getByRole("checkbox")).toBeDisabled();
  });
});
