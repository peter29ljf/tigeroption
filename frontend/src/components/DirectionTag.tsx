import clsx from "clsx";

const directionConfig = {
  BULLISH: { label: "看涨", arrow: "↑", cls: "bg-green-500/15 text-green-400 border-green-500/30" },
  BEARISH: { label: "看跌", arrow: "↓", cls: "bg-red-500/15 text-red-400 border-red-500/30" },
  NEUTRAL: { label: "中性", arrow: "→", cls: "bg-gray-500/15 text-gray-400 border-gray-500/30" },
} as const;

export function DirectionTag({ direction }: { direction: "BULLISH" | "BEARISH" | "NEUTRAL" }) {
  const config = directionConfig[direction] ?? directionConfig.NEUTRAL;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border",
        config.cls
      )}
    >
      <span>{config.arrow}</span>
      {config.label}
    </span>
  );
}
