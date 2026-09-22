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
    <div className="overflow-y-auto max-h-64 bg-zinc-950 rounded-sm p-3 font-mono text-xs text-zinc-300 leading-relaxed">
      <pre className="whitespace-pre-wrap wrap-break-word">{tokens}</pre>
      {/* Curseur de frappe : un bloc dessiné, pas le caractère `█`, dont la
          largeur dépend de la police du système. */}
      {isActive && (
        <span className="ml-0.5 inline-block h-3 w-1.5 animate-pulse bg-blue-400 align-text-bottom" />
      )}
      <div ref={bottomRef} />
    </div>
  );
}
