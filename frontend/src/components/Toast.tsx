import type { Toast as ToastItem } from "../hooks/useToast";

const TYPE_STYLE: Record<ToastItem["type"], string> = {
  success: "bg-green-800 text-green-100",
  error: "bg-red-800 text-red-100",
  info: "bg-zinc-700 text-zinc-100",
};

const TYPE_ICON: Record<ToastItem["type"], string> = {
  success: "✓",
  error: "✗",
  info: "ℹ",
};

interface ToastItemProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

function ToastRow({ toast, onDismiss }: ToastItemProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      data-type={toast.type}
      className={`flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${TYPE_STYLE[toast.type]}`}
    >
      <span>{TYPE_ICON[toast.type]}</span>
      <span className="flex-1">{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        aria-label="Fermer"
        className="ml-2 opacity-70 hover:opacity-100 transition-opacity"
      >
        ×
      </button>
    </div>
  );
}

interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

export default function ToastContainer({
  toasts,
  onDismiss,
}: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <ToastRow key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
