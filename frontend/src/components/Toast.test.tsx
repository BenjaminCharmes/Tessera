import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ToastContainer from "./Toast";
import type { Toast } from "../hooks/useToast";

const SUCCESS_TOAST: Toast = {
  id: "t1",
  message: "Projet créé",
  type: "success",
  duration: 3000,
};

const ERROR_TOAST: Toast = {
  id: "t2",
  message: "Erreur API",
  type: "error",
  duration: 3000,
};

const INFO_TOAST: Toast = {
  id: "t3",
  message: "Information",
  type: "info",
  duration: 3000,
};

describe("ToastContainer", () => {
  it("renders nothing when toasts array is empty", () => {
    const { container } = render(
      <ToastContainer toasts={[]} onDismiss={vi.fn()} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders a success toast", () => {
    render(<ToastContainer toasts={[SUCCESS_TOAST]} onDismiss={vi.fn()} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Projet créé")).toBeInTheDocument();
  });

  it("renders an error toast", () => {
    render(<ToastContainer toasts={[ERROR_TOAST]} onDismiss={vi.fn()} />);
    expect(screen.getByText("Erreur API")).toBeInTheDocument();
  });

  it("renders an info toast", () => {
    render(<ToastContainer toasts={[INFO_TOAST]} onDismiss={vi.fn()} />);
    expect(screen.getByText("Information")).toBeInTheDocument();
  });

  it("renders multiple toasts", () => {
    render(
      <ToastContainer
        toasts={[SUCCESS_TOAST, ERROR_TOAST]}
        onDismiss={vi.fn()}
      />,
    );
    expect(screen.getAllByRole("status")).toHaveLength(2);
  });

  it("calls onDismiss with the toast id when close button is clicked", async () => {
    const onDismiss = vi.fn();
    render(<ToastContainer toasts={[SUCCESS_TOAST]} onDismiss={onDismiss} />);
    await userEvent.click(screen.getByLabelText("Fermer"));
    expect(onDismiss).toHaveBeenCalledWith("t1");
  });
});
