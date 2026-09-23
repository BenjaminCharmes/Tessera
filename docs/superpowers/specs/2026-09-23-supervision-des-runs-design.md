# Supervision des runs — design

**Date** : 2026-09-23
**Statut** : validé, prêt pour le plan d'implémentation
**Tickets** : ticket-127 (registre et hub), ticket-128 (lancement POST et
canal d'observation), ticket-129 (vue Supervision et badge)

---

## Le problème

Le WebSocket de run (`routers/orchestrator.py:378`, `WS /orchestrator/stream/{project_id}`)
**déclenche** le run : le client envoie le payload de démarrage à l'ouverture,
et l'émetteur construit par `pipeline_stream.emetteur()` écrit sur cette
socket et sur elle seule.

Trois conséquences, toutes visibles à l'usage :

1. Un run n'est observable que par l'onglet qui l'a lancé. Recharger la page
   rend aveugle jusqu'à la fin du run, alors que le backend continue.
2. Il n'existe aucune vue de ce qui tourne sur la machine. `RunLock` sait quel
   projet est occupé et sur quel ticket, mais rien n'expose cet état.
3. Répondre à un agent qui pose une question (ADR-025) n'est possible que
   depuis cette même socket, donc depuis ce même onglet.

Le parallélisme réel de Tessera est **entre projets** (ADR-038 : un run par
projet, N projets simultanés). C'est précisément ce que l'UI ne montre pas.

## Ce qu'on construit

Un « mission control » : une vue de tous les runs actifs, tous projets
confondus, avec le détail complet — tokens compris — du run qu'on sélectionne.

### Décisions de cadrage

| Question | Choix |
|---|---|
| Périmètre | Tous les projets, pas seulement l'actif |
| Rattrapage au rechargement | **Non.** On observe le présent ; l'historique reste dans `RunHistory` |
| Détail disponible | Tout, tokens compris |
| Mode de livraison du détail | **À l'abonnement** — transitions poussées pour tous, tokens pour le run sélectionné |
| Placement | Vue centrale dans le NavRail + badge permanent |
| Découplage run/socket | **Oui, dans ce chantier** |

**Hors périmètre, assumé** : le chat (ADR-019) garde sa socket
`/chat/{project_id}` et n'apparaît pas dans le mission control. Il produit du
travail commité, donc il y a sa place à terme — consigné en ticket séparé.

---

## Architecture

### `RunRegistry` — l'état vivant

Un objet en mémoire du process, de même nature et de même durée de vie que
`RunLock` (`services/run_lock.py`), et pour la même raison : un backend local
n'a pas de second process à protéger.

Il tient un `RunActif` par run :

- `run_id`, `project_id`, `mode` (`single` | `queue` | `autonomous`)
- ticket courant, étape courante, agent courant
- `demarre_a`, tour de revue
- compteurs : tokens entrée/sortie, coût estimé
- dernier verdict connu
- le `DialogueChannel` du run

**Il remplace le dictionnaire interne de `RunLock`.** Deux structures qui
décrivent « ce qui tourne » divergeraient (ADR-034) ; `RunLock` garde son API
publique — `is_running`, `ticket_en_cours`, `acquire` — et délègue au
registre. `RunAlreadyInProgress` et son message ne bougent pas.

### `EventHub` — la diffusion

Publication/abonnement en mémoire. L'orchestrateur publie **tous** ses
événements ; chaque observateur reçoit une file `asyncio` bornée.

Règle de débordement, qui est le cœur du contrat : **une file pleine jette les
`agent_token` et `agent_tool_use`, jamais les transitions.** Un client lent ne
doit ni ralentir un run, ni faire disparaître un verdict, un commit ou un
changement de statut. Perdre du texte dégrade l'affichage ; perdre une
transition le rend faux.

L'émetteur actuel garde ses deux propriétés : il tolère une socket morte
(ticket-079) et persiste l'événement **après** l'envoi.

### Le démarrage d'un run

`POST /api/v1/orchestrator/run` couvre les trois modes, démarre une tâche
`asyncio`, et renvoie `{"run_id": ...}` immédiatement. Le verrou projet est
acquis **dans la tâche**, et un projet déjà occupé répond 409 comme
aujourd'hui.

**`WS /orchestrator/stream/{project_id}` est supprimé.** Deux façons de lancer
un run divergeraient, et la seconde n'aurait plus de raison d'être une fois le
canal d'observation en place.

Effet de bord bénéfique : aujourd'hui seul le mode `single` passe un `run_id`
à l'émetteur (`pipeline_stream.py` — `run_autonomous` et `_stream_file`
passent `run_id=None`), donc file et autonome n'ont **aucun historique en
base**. Le registre les enregistre tous.

### `WS /api/v1/orchestrator/observe` — le canal

Sans projet dans l'URL. Authentifié comme les autres routes WebSocket
(`STATIC_TOKEN`, cf. ticket-120).

**Serveur → client**

- à la connexion, un instantané : tous les `RunActif` du registre ;
- ensuite, les transitions de tous les runs — `agent_started`, `agent_done`,
  `branch_created`, `commit_created`, `ticket_status_changed`, `test_result`,
  `security_audit_*`, `validation_done`, `doc_updated`, `quota_updated`,
  `queue_progress`, `livraison_done`, `pipeline_done`, `error`,
  `agent_question` ;
- pour chaque run auquel le client s'est abonné, en plus : `agent_token` et
  `agent_tool_use`.

Chaque message porte son `run_id` et son `project_id`.

**Client → serveur**

- `{"subscribe": "<run_id>"}` / `{"unsubscribe": "<run_id>"}`
- `{"type": "answer" | "interject" | "stop", "run_id": "...", "text": "..."}`
  — routé vers le `DialogueChannel` que le registre détient pour ce run.

`DialogueChannel` annonce déjà ne rien savoir du transport : c'est ce qui rend
ce routage possible sans toucher à la sémantique d'ADR-025. Le délai
d'attente, la reprise sur hypothèse énoncée et le silence du mode autonome
sont inchangés.

---

## L'UI

### Badge

Une pastille sur une destination « Supervision » du `NavRail`, dans les cinq
familles d'ADR-026 :

- `blue` — n runs tournent
- `amber` — au moins un agent attend une réponse
- `red` — au moins un run bloqué
- rien — aucun run

**Le nombre est celui des runs, pas des agents.** Un pipeline Tessera est
séquentiel : il n'y a jamais deux agents simultanés dans un même run.
Annoncer « 12 agents » serait faux.

### Vue Supervision

Vue centrale, à côté de Kanban / Runs / Coûts. Deux colonnes.

**Gauche — les runs actifs.** Une carte par run : nom du projet en violet
(identité, ADR-026), mode, ticket courant, étape et agent courants, chrono
depuis `demarre_a`, tokens, coût, tour de revue. La carte sélectionnée porte
une **barre** violette — jamais de texte coloré (ADR-026).

**Droite — le run sélectionné**, et c'est ce qui matérialise l'abonnement :
`TokenStream`, outils appelés, `VerdictBanner`, et `AgentDialogue` pour
répondre, interjeter ou arrêter.

Cinq composants d'`AgentPanel/` sont réutilisés tels quels — `TokenStream`,
`AgentBlock`, `VerdictBanner`, `AgentDialogue`, `RoundBadge`. Le travail est
d'assembler, pas de dessiner.

**État vide** : aucun run actif — la vue le dit et renvoie vers le Kanban.

### `useSupervision`

Un seul WebSocket, monté une fois dans `App`, diffusé par un Context React.

Ça frôle **ADR-013** (pas de gestionnaire d'état global) sans le violer : un
Context natif n'est ni Zustand ni Jotai, et l'alternative — un socket par
composant — ouvrirait N connexions pour une source unique. Noté ici pour que
ce soit une décision lisible et non une découverte en revue.

Le hook gère : instantané initial, abonnement/désabonnement au changement de
sélection, reconnexion avec renvoi de l'abonnement courant.

### `AgentPanel` après le changement

Il garde son rôle — observer le projet actif dans la colonne de droite — mais
consomme désormais le canal d'observation filtré sur ce projet, au lieu de sa
propre socket. `useOrchestratorStream` disparaît au profit de
`useSupervision`.

---

## Tests

**Backend**

- le hub diffuse à N abonnés ;
- une file pleine jette les tokens et **jamais** les transitions ;
- le run survit à la déconnexion du client qui l'a lancé ;
- une réponse de dialogue atteint le bon run quand deux runs tournent ;
- `subscribe` ajoute les tokens d'un run et d'un seul ;
- les trois modes sont enregistrés en base, pas seulement `single` ;
- `RunLock` conserve son comportement : 409 nommant le ticket en cours ;
- `POST /orchestrator/run` répond avant la fin du run.

**Frontend**

- `useSupervision` : instantané, abonnement au changement de sélection,
  reconnexion ;
- la colonne gauche liste un run par projet actif, chrono compris ;
- le badge suit les quatre états ;
- état vide.

**Cohérence**

`design/coherence.test.ts` et `identite.test.ts` couvrent déjà ADR-026 ; les
nouveaux composants y passent sans ajout. `test_consignes_coherentes.py`
vérifie le budget du nouvel ADR.

---

## ADR

Un ADR nouveau — **un run est observé, pas possédé** — qui pose le registre,
le hub et la suppression du lancement par socket. Il amende :

- **ADR-025** : le dialogue passe par le registre, plus par la socket
  lanceuse. La sémantique — délai, hypothèse énoncée, file distincte des
  interjections — est inchangée ;
- **ADR-008** : le registre rejoint `RunLock` comme état en mémoire assumé.
  L'orchestrateur reste instancié par requête ; ce qui persiste, c'est le
  suivi des runs, pas le moteur.

Rédigé avec le skill `write-adr`, budget compris.

---

## Ce qui est consigné et pas fait

- le chat (ADR-019) dans le mission control ;
- le cleanup des ADR — quarante entrées, dont quatre déjà amendées ;
- un ticket d'amorçage par axe restant : bouton « lancer le projet », Carrière
  en webapp, gestion du freelance, reprise du portfolio, projet from-scratch
  piloté par Tessera.
