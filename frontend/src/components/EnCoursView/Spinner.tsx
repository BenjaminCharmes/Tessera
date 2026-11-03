/** Un cercle qui tourne : l'opération est partie, pas encore constatée. */
export default function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="inline-block size-3 animate-spin rounded-full border-2 border-zinc-500 border-t-transparent"
    />
  );
}
