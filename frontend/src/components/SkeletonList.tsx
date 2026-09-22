interface SkeletonListProps {
  count?: number;
}

function SkeletonItem() {
  return <div className="h-8 mx-3 my-1 rounded-sm bg-zinc-800 animate-pulse" />;
}

export default function SkeletonList({ count = 3 }: SkeletonListProps) {
  return (
    <div className="py-1">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonItem key={i} />
      ))}
    </div>
  );
}
