---
id: ticket-123
title: "Remonter la branche du run, annuler les réponses obsolètes, lint en CI"
type: fix
status: done
pr_number: 145
priority: high
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-22
---

# ticket-123 — Remonter la branche du run, annuler les réponses obsolètes, lint en CI

## Objectif

Que l'UI reflète le run réel après sa fin, ne mélange pas les projets, et que
le lint soit mesuré.

## Contexte

- `useOrchestratorStream` construit `PipelineResult` sans `branch` ; le
  backend n'émet pas `branch` dans `pipeline_done` et le hook ignore
  `branch_created`. `TicketActivity` affiche « Lance d'abord le pipeline »
  après un run approuvé, bouton PR désactivé.
- `useTickets` : `processedEventsRef` n'est remis à jour que si
  `newEvents.length > 0` ; après `stream.clear()` les premiers
  `ticket_status_changed` du run suivant sont ignorés.
- `useRuns`, `useUsage`, `Editor.readFile` n'annulent pas les réponses au
  changement de projet ou de fichier ; `useTickets`, `useChat`, `DiffView`,
  `CostView` le font. Cinq hooks « fetch + loading + error » quasi identiques.
- `useChat` : `onClose` propre → `idle`, `ChatPanel` exige `ready` : textarea
  actif, bouton grisé, sans message ni reconnexion.
- `npm run lint` : 19 erreurs (16 `react-hooks/set-state-in-effect`, 2
  `no-unsafe-function-type` dans e2e, 1 faux positif `rules-of-hooks` sur la
  fixture Playwright `use`). Ni la CI ni `verify` ne lancent eslint.
- Code mort : `hooks/usePipeline.ts`, `components/PipelineToast.tsx` ;
  `TicketCard` attend `githubRemote` / `onPrCreated` jamais fournis ;
  `tour {runningRound}/3` en dur.
- Accessibilité : `TicketCard` est un `div onClick` sans clavier ;
  `ProjectNav` imbrique `<a>` dans `<button>`.

## Solution proposée

1. Backend : `emit(PIPELINE_DONE, …, branch=run.branch)` sur les quatre
   sorties (`pipeline_outcomes.py`, modification minimale : ajouter le champ,
   rien d'autre — ticket-121 retravaille ces fonctions en parallèle).
   Frontend : `PipelineResult.branch` lu depuis l'événement, et
   `branch_created` mémorisé dans le hook.
2. `processedEventsRef` remis à `events.length` quand `events.length` diminue.
3. Un hook `useResource<T>(fetcher, deps)` avec flag d'annulation ; `useRuns`,
   `useUsage`, `useAgents`, `useProjects` l'utilisent. `Editor` annule sa
   lecture précédente.
4. `useChat` : statut `disconnected` distinct d'`idle`, message dans le panel,
   reconnexion au prochain envoi.
5. Lint : corriger les 16 `set-state-in-effect` (dériver l'état ou passer par
   `useResource`), typer les deux `Function`, exclure `e2e/` de la règle
   `rules-of-hooks`. Ajouter `npm run lint` au job frontend de `ci.yml` et à
   `tessera.ps1 verify`.
6. Supprimer `usePipeline`, `PipelineToast` et leurs tests ; passer
   `githubRemote` et `onPrCreated` depuis `TicketList` / `KanbanColumn` ;
   `maxRounds` lu depuis l'événement de run.
7. `TicketCard` : `role="button"`, `tabIndex=0`, Enter/Espace. `ProjectNav` :
   `<a>` hors du `<button>`.

Hors périmètre : convention kebab-case des fichiers, découpage des fichiers
> 200 lignes, app Tauri et `lib/api.ts`/`lib/ws.ts` (ticket-124), en-tête
d'authentification (ticket-120).

## Critères d'acceptation

- [ ] Test hook : après `pipeline_done` avec `branch`, `lastResult.branch` est
      renseigné ; test backend : `pipeline_done` porte `branch`
- [ ] Test : après `clear()` puis un `ticket_status_changed`, `useTickets` le
      traite
- [ ] Test : changement de projet pendant un fetch en cours → l'état final est
      celui du second projet (pour `useRuns` et `useUsage`)
- [ ] `npm run lint` sort sans erreur et tourne dans `ci.yml`
- [ ] `grep -rn "usePipeline\|PipelineToast" frontend/src` ne renvoie rien
- [ ] Test RTL : `TicketCard` s'ouvre à la touche Entrée
- [ ] `npm run typecheck`, `npm run test`, `npm run build`,
      `uv run pytest -q` verts

## Ce que ça ne fait pas

- **`maxRounds` reste vide.** Le hook lit `max_rounds` sur les événements de
  run, mais le backend ne l'émet pas : `max_review_rounds` vit dans la config
  du pipeline (`models/agent.py`) et ne sort jamais sur le flux. La carte
  affiche donc « tour N » sans dénominateur ; le « /3 » en dur est parti,
  pas remplacé. L'émission côté backend attend ticket-121, qui retravaille
  `pipeline_outcomes.py` en parallèle — on n'y touche pas ici.
- **`onPrCreated` traverse quatre niveaux.** `App` → `Sidebar` → `TicketList`
  → `TicketCard`, et `App` → `KanbanView` → `KanbanColumn` → `TicketCard`.
  C'est le chemin qu'empruntent déjà tous les autres rappels ; un store
  (ADR-013) n'est pas justifié pour un seul de plus.
- **`useResource` ne remplace pas tout.** `useTickets`, `useChat` et
  `useGitStatus` gardent leur propre machine à états : ils mêlent flux
  WebSocket, événements et écritures, et les plier dans « une requête, une
  réponse » les aurait déformés. `useChat` applique le même principe
  (état clé par conversation, aucun `setState` synchrone dans un effet) sans
  passer par le hook.
- **`GitLinkPanel` relit le mode des artefacts à chaque changement de statut
  git**, comme avant. Le statut fait partie de la clé de la requête même si
  la requête ne le lit pas ; c'est dit dans le code plutôt que caché.
- **Pas de reconnexion automatique du chat.** Une socket fermée proprement
  attend le prochain envoi ; un serveur redémarré n'a pas à recevoir une
  rafale de reconnexions de panneaux inactifs.
- **La règle `rules-of-hooks` est coupée sur `e2e/**` seulement**, pour la
  fixture Playwright `use`. Le reste du lint s'applique aux tests e2e.
- **Playwright n'est pas relancé ici** : `npm run test:e2e` demande les
  navigateurs installés ; la CI le fait dans son job `e2e`.

## Dépendances
Aucune.

## Estimation
2 jours.

## Risques
Les corrections `set-state-in-effect` changent le moment où l'état se pose :
les tests RTL existants doivent rester verts sans `act` supplémentaire.
