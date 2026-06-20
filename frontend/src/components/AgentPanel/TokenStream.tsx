import { useEffect, useRef } from "react";

interface TokenStreamProps {
  tokens: string;
  isActive: boolean;
}

export default function TokenStream({ tokens, isActive }: TokenStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [tokens]);

  return (
    <div className="overflow-y-auto max-h-64 bg-zinc-950 rounded p-3 font-mono text-xs text-zinc-300 leading-relaxed">
      <pre className="whitespace-pre-wrap break-words">{tokens}</pre>
      {isActive && <span className="text-blue-400 animate-pulse">█</span>}
      <div ref={bottomRef} />
    </div>
  );
}
