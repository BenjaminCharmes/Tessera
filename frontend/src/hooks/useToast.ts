import { useCallback, useState } from "react";

export interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info";
  duration: number;
}

export interface UseToastResult {
  toasts: Toast[];
  addToast: (message: string, type: Toast["type"], duration?: number) => void;
  removeToast: (id: string) => void;
}

let counter = 0;

export function useToast(): UseToastResult {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message: string, type: Toast["type"], duration = 3000) => {
      const id = `toast-${++counter}`;
      const toast: Toast = { id, message, type, duration };
      setToasts((prev) => [...prev, toast]);
      if (duration > 0) {
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== id));
        }, duration);
      }
    },
    [],
  );

  return { toasts, addToast, removeToast };
}
