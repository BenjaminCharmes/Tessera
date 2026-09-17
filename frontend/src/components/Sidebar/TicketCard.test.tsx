import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import TicketCard from "./TicketCard";
import type { Ticket } from "../../types/api";
import * as apiModule from "../../lib/api";

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
  pr_number: null,
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

  it("calls onRun with ticket id when run button clicked", () => {
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
    fireEvent.click(screen.getByRole("button", { name: "Lancer le pipeline" }));
    expect(onRun).toHaveBeenCalledWith("ticket-001");
  });

  it("run click does not bubble to onSelect", () => {
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
    fireEvent.click(screen.getByRole("button", { name: "Lancer le pipeline" }));
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
    const pulse = document.querySelector(".animate-pulse")!;
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
    expect(screen.getByRole("button", { name: "Lancer le pipeline" })).toBeDisabled();
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

  // ------------------------------------------------------------------
  // PR button
  // ------------------------------------------------------------------

  it("no PR button when ticket is not done", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "in-progress" }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.queryByTitle("Ouvrir une PR")).not.toBeInTheDocument();
  });

  it("no PR button when githubRemote is absent", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "done" }}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.queryByTitle("Ouvrir une PR")).not.toBeInTheDocument();
  });

  it("no PR button when pr_number already set", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "done", pr_number: 15 }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.queryByTitle("Ouvrir une PR")).not.toBeInTheDocument();
  });

  it("shows PR button when ticket done + githubRemote + no pr_number", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "done" }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByTitle("Ouvrir une PR")).toBeInTheDocument();
  });

  it("PR button click shows inline branch form", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "done" }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTitle("Ouvrir une PR"));
    expect(screen.getByPlaceholderText("branch name")).toBeInTheDocument();
  });

  it("branch input pre-filled with ticket id", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "done" }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTitle("Ouvrir une PR"));
    expect(screen.getByPlaceholderText("branch name")).toHaveValue(
      "ticket-001",
    );
  });

  it("cancel button hides the form", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "done" }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTitle("Ouvrir une PR"));
    fireEvent.click(screen.getByRole("button", { name: "Annuler" }));
    expect(
      screen.queryByPlaceholderText("branch name"),
    ).not.toBeInTheDocument();
  });

  it("submitting form calls api.github.createPr and onPrCreated", async () => {
    const createPr = vi
      .spyOn(apiModule.api.github, "createPr")
      .mockResolvedValue({
        pr_number: 42,
        pr_url: "https://github.com/owner/repo/pull/42",
      });
    const getPrStatus = vi
      .spyOn(apiModule.api.github, "getPrStatus")
      .mockResolvedValue({
        state: "open",
        ci_status: "none",
        pr_url: "https://github.com/owner/repo/pull/42",
        pr_number: 42,
      });

    const onPrCreated = vi.fn();
    render(
      <TicketCard
        ticket={{ ...base, status: "done" }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
        onPrCreated={onPrCreated}
      />,
    );

    fireEvent.click(screen.getByTitle("Ouvrir une PR"));
    fireEvent.submit(
      screen.getByPlaceholderText("branch name").closest("form")!,
    );

    await waitFor(() => {
      expect(createPr).toHaveBeenCalledWith(
        "ide-core",
        "ticket-001",
        "ticket-001",
      );
      expect(onPrCreated).toHaveBeenCalledWith("ticket-001", 42);
    });

    createPr.mockRestore();
    getPrStatus.mockRestore();
  });

  // ------------------------------------------------------------------
  // PR badge
  // ------------------------------------------------------------------

  it("shows PR number badge when pr_number set", () => {
    vi.spyOn(apiModule.api.github, "getPrStatus").mockResolvedValue({
      state: "open",
      ci_status: "none",
      pr_url: "https://github.com/owner/repo/pull/7",
      pr_number: 7,
    });

    render(
      <TicketCard
        ticket={{ ...base, pr_number: 7 }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByText("PR #7")).toBeInTheDocument();
  });

  it("shows CI status badge after polling resolves", async () => {
    vi.spyOn(apiModule.api.github, "getPrStatus").mockResolvedValue({
      state: "open",
      ci_status: "passing",
      pr_url: "https://github.com/owner/repo/pull/7",
      pr_number: 7,
    });

    render(
      <TicketCard
        ticket={{ ...base, pr_number: 7 }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("CI verte")).toBeInTheDocument();
    });
  });
});
