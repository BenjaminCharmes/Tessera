/**
 * Les projets dont un run attend une réponse — ticket-186.
 *
 * La question ne se voyait que dans le panneau du projet sélectionné et sur
 * la carte de Supervision : depuis l'onglet Tickets d'un autre projet, rien.
 * Un agent a attendu ses cinq minutes sans que personne ne le sache.
 */
export function projetsEnAttente(
  runs: readonly { run_id: string; project_id: string }[],
  questionDe: (runId: string) => string | null,
): Set<string> {
  const attendent = new Set<string>();
  for (const run of runs) {
    if (questionDe(run.run_id) !== null) attendent.add(run.project_id);
  }
  return attendent;
}
