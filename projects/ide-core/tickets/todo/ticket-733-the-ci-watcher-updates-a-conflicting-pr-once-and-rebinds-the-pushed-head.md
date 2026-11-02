---
id: ticket-733
title: "The CI watcher updates a conflicting PR once and rebinds the pushed head"
type: feat
status: todo
priority: low
agent: codeur
depends_on: [ticket-732]
created: 2026-11-02
---

# ticket-733 — Le watcher met à jour une PR conflictuelle, une fois, et relie la nouvelle tête

## Contexte

ADR-069 (conception : ticket-674). `mettre_a_jour_branche` (ticket-732) fait le
geste ; ce ticket décide **quand** et fait suivre l'approbation.

Rappel de ce qui existe : le merge est lié à `pushed_sha` (ticket-492), relu après
la CI ; `ControleTete` refuse une tête qui n'est pas le commit poussé ;
`reprendre_surveillances` relit `pushed_sha` en base. Une mise à jour change la
tête : sans lien refait, le watcher refuserait sa propre mise à jour.

## Contrat

1. `Livraison` gagne `a_mettre_a_jour: bool = False`. `livrer_phase_2` le pose
   quand la CI rend `conflicting` ; le texte de `arret` ne change pas.
2. `CIWatcher.surveiller(..., mise_a_jour: MiseAJourPr | None = None)` avec
   `MiseAJourPr = Callable[[str], Awaitable[MiseAJour]]` (argument : la tête
   attendue). `None` : comportement actuel, « à rebaser ».
3. Dans `_livrer_et_emettre`, quand la phase 2 rend `a_mettre_a_jour` et
   qu'aucune mise à jour n'a encore eu lieu pour cette surveillance :
   a. la tête a déjà été contrôlée contre `pushed_sha` avant la phase 2 ; elle
      est relue juste avant d'appeler `mise_a_jour(pushed_sha)` ;
   b. sur `arret`, échec habituel (`ticket_status_changed` blocked +
      `ci_merge_done` merged=False), l'arrêt commençant par « mise à jour
      refusée : » ;
   c. sur `sha`, **avant** toute attente de CI : `pushed_sha` du dernier run du
      ticket qui en porte un devient `sha` (nouvelle fonction
      `noter_poussee_du_ticket` dans `sha_approbation.py`). Écriture impossible :
      échec fermé, PR laissée ouverte (ADR-039) ;
   d. `ControleTete` est reconstruit avec la nouvelle tête, la fenêtre de
      relecture de ticket-527 attend que GitHub la montre, puis la phase 2 repart
      avec `sha_attendu=sha` ;
   e. un second `conflicting` n'appelle pas de seconde mise à jour : échec
      habituel « à rebaser ».
4. Bornes : le délai de phase 2 s'applique à chaque passage ; la mise à jour a la
   sienne (300 s). Un dépassement bloque le ticket et nomme la cause.
5. Une ligne de `pipeline-log.md` — `[ticket-N] PR #P mise à jour avec <base> :
   <ancienne tête 7> → <nouvelle tête 7>` — quand le watcher a un chemin de
   journal ; sans lui (projet en worktree, ADR-056), seul l'événement la porte.
6. `surveillance_pour` fournit `mise_a_jour` : dépôt du projet, base de la
   politique, et le retest du projet quand il en déclare un. `ticket_proposal.py`
   ne le fournit pas : ses PR ne changent pas de comportement.
7. Le merge qui suit reste automatique à CI verte (ou `merge_without_ci`) :
   ni résolution d'agent, ni `conflits` posé. ADR-033 ne s'applique pas.

## Critères d'acceptation

- [ ] Test `CIWatcher` : phase 2 `conflicting`, `mise_a_jour` rend une tête → la tête est notée en base, la phase 2 repart avec cette tête comme `sha_attendu`, la PR est mergée
- [ ] Test : `mise_a_jour` rend un `arret` → ticket `blocked`, `ci_merge_done` merged=False, arrêt « mise à jour refusée : … », PR ouverte
- [ ] Test : une tête de PR qui n'est plus `pushed_sha` avant la mise à jour → aucun appel à `mise_a_jour`, arrêt « tête changée » habituel
- [ ] Test : second `conflicting` après la mise à jour → un seul appel à `mise_a_jour`, ticket `blocked`
- [ ] Test : écriture de `pushed_sha` en échec → ticket `blocked`, aucune attente de CI
- [ ] Test : sans `mise_a_jour`, le comportement et le texte de l'arrêt sont ceux d'aujourd'hui
- [ ] Test de reprise : après redémarrage, une PR dont la tête est la tête mise à jour est reprise et mergée ; `sha_pousse_du_ticket` rend cette tête
- [ ] Test : une mise à jour qui dépasse sa borne bloque le ticket avec un arrêt qui cite le délai
- [ ] `docs/architecture.md` n'est pas touché : la documentation se met à jour par lot (ADR-035)
- [ ] Fichiers sous 300 lignes ; `scripts/verifier.py` passe

## Ce que ça ne fait pas

- Ne met à jour aucune PR sous autonomie `pr` ou `commit` : la phase 2 n'y attend rien.
- Ne tente aucune résolution par un agent, même sur un conflit que les règles ne résolvent pas.
- N'ajoute ni colonne ni table : `pushed_sha` garde son sens, « la dernière tête que le pipeline a poussée ».
