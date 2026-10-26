/** La rangée d'un projet sans run, en bas de la vue compacte : rien ne se dessine, le mot suffit. */
export default function AuRepos({ projet }: { projet: string }) {
  return (
    <div
      role="group"
      aria-label={`${projet}, au repos`}
      className="flex items-center gap-3 rounded-md border border-zinc-800 px-3 py-2"
    >
      <span className="w-40 truncate text-corps text-zinc-400">{projet}</span>
      <span className="text-micro text-zinc-500">au repos</span>
    </div>
  );
}
