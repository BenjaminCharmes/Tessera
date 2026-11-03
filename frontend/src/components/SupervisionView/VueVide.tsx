interface VueVideProps {
  connecte: boolean;
  avecServices: boolean;
}

/** Ce que Supervision dit quand aucun run ne tourne. */
export default function VueVide({ connecte, avecServices }: VueVideProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
      <p className="text-sm text-zinc-400">
        {!connecte
          ? "En attente du canal d'observation…"
          : avecServices
            ? "Aucun run en cours — mais des services tournent."
            : "Aucun run en cours."}
      </p>
      <p className="max-w-sm text-xs text-zinc-600">
        Lance un ticket depuis le tableau : il apparaîtra ici, quel que soit le
        projet, et restera visible même si tu changes de vue.
      </p>
    </div>
  );
}
