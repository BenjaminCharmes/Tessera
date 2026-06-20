interface RoundBadgeProps {
  current: number;
  max?: number;
}

export default function RoundBadge({ current, max = 3 }: RoundBadgeProps) {
  const pct = Math.min((current / max) * 100, 100);

  return (
    <div className="flex items-center gap-2 px-4 py-2">
      <span className="text-xs font-semibold text-blue-400 shrink-0">
        Tour {current} / {max}
      </span>
      <div className="flex-1 h-1 bg-zinc-700 rounded-full">
        <div
          className="h-1 bg-blue-500 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
