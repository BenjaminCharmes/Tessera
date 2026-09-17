import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import QueueBar from "./QueueBar";

describe("QueueBar", () => {
  it("ne s'affiche pas sans selection", () => {
    const { container } = render(
      <QueueBar selection={[]} onRun={() => {}} onClear={() => {}} enCours={false} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("annonce combien de tickets partiront, et dans quel ordre", () => {
    render(
      <QueueBar
        selection={["ticket-003", "ticket-001"]}
        onRun={() => {}}
        onClear={() => {}}
        enCours={false}
      />,
    );

    expect(screen.getByText(/2 tickets/i)).toBeInTheDocument();
    expect(screen.getByText(/ticket-003, ticket-001/)).toBeInTheDocument();
  });

  it("lance la file au clic", async () => {
    const onRun = vi.fn();
    render(
      <QueueBar
        selection={["ticket-001"]}
        onRun={onRun}
        onClear={() => {}}
        enCours={false}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /lancer/i }));

    expect(onRun).toHaveBeenCalled();
  });

  it("ne propose pas de relancer pendant qu'une file tourne", () => {
    render(
      <QueueBar
        selection={["ticket-001"]}
        onRun={() => {}}
        onClear={() => {}}
        enCours
      />,
    );

    expect(screen.getByRole("button", { name: /lancer/i })).toBeDisabled();
  });
});
