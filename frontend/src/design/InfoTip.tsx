import { useId, useState } from "react";
import type { ReactNode } from "react";
import { IconInfo } from "./icons";

interface InfoTipProps {
  /** The explanatory text shown in the tooltip on hover or keyboard focus. */
  children: ReactNode;
}

/**
 * An information icon paired with a tooltip — ticket-273.
 *
 * Use for explanatory text only: what a setting does, why something exists.
 * States, calls to action and errors stay permanently visible — hiding them
 * would bury the information at the moment it matters.
 *
 * Accessible via keyboard: Tab focuses the icon, Escape closes the tooltip.
 * Colors stay in the zinc family (ADR-026: no violet in text).
 */
export default function InfoTip({ children }: InfoTipProps) {
  const [ouvert, setOuvert] = useState(false);
  const tooltipId = useId();

  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        aria-label="Plus d'informations"
        aria-describedby={tooltipId}
        className="rounded-sm text-zinc-500 hover:text-zinc-300 focus:outline-hidden focus-visible:ring-1 focus-visible:ring-zinc-500"
        onMouseEnter={() => setOuvert(true)}
        onMouseLeave={() => setOuvert(false)}
        onFocus={() => setOuvert(true)}
        onBlur={() => setOuvert(false)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOuvert(false);
        }}
      >
        <IconInfo size={14} />
      </button>
      {ouvert && (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute left-5 top-0 z-50 w-56 rounded-sm border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-micro text-zinc-400 shadow-lg"
        >
          {children}
        </span>
      )}
    </span>
  );
}
