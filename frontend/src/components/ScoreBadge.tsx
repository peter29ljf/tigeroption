import clsx from "clsx";

export function ScoreBadge({ score }: { score: number }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-semibold min-w-[40px]",
        score >= 70 && "bg-green-500/20 text-green-400",
        score >= 40 && score < 70 && "bg-yellow-500/20 text-yellow-400",
        score < 40 && "bg-red-500/20 text-red-400"
      )}
    >
      {score}
    </span>
  );
}
