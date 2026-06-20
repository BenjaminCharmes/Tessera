import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TicketCard from "./TicketCard";
import type { Ticket } from "../../types/api";

const base: Ticket = {
  id: "ticket-001",
  title: "Add authentication module",
  type: "feat",
  status: "todo",
  priority: "high",
  agent: "codeur",
  depends_on: [],
  created: "2026-06-20",
  github_issue_url: null,
  body: "Implement OAuth2 login flow",
  project_id: "ide-core",
  file_path: "/projects/ide-core/tickets/todo/ticket-001.md",
};

describe("TicketCard", () => {
  it("renders ticket id and title", () => {
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByText("ticket-001")).toBeInTheDocument();
    expect(screen.getByText("Add authentication module")).toBeInTheDocument();
  });

  it("renders status and priority badges", () => {
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByText("todo")).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("calls onSelect when card is clicked", () => {
    const onSelect = vi.fn();
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={onSelect}
        onRun={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("Add authentication module"));
    expect(onSelect).toHaveBeenCalledWith(base);
  });

  it("calls onRun with ticket id when ▶ button clicked", () => {
    const onRun = vi.fn();
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={onRun}
      />,
    );
    fireEvent.click(screen.getByTitle("Run pipeline"));
    expect(onRun).toHaveBeenCalledWith("ticket-001");
  });

  it("▶ click does not bubble to onSelect", () => {
    const onSelect = vi.fn();
    const onRun = vi.fn();
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={onSelect}
        onRun={onRun}
      />,
    );
    fireEvent.click(screen.getByTitle("Run pipeline"));
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("shows animate-pulse indicator when running", () => {
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={true}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    const pulse = screen.getByText("●");
    expect(pulse).toHaveClass("animate-pulse");
  });

  it("run button is disabled when running", () => {
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={true}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByTitle("Run pipeline")).toBeDisabled();
  });

  it("no run button for done tickets", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "done" }}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.queryByTitle("Run pipeline")).not.toBeInTheDocument();
  });

  it("no run button for cancelled tickets", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "cancelled" }}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.queryByTitle("Run pipeline")).not.toBeInTheDocument();
  });

  it("applies active styling when isActive", () => {
    const { container } = render(
      <TicketCard
        ticket={base}
        isActive={true}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(container.firstChild).toHaveClass("bg-zinc-700");
  });
});
