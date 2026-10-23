# Vue Bureau — conception (ticket-550, ADR-058)

## Ce que c'est

La vue par défaut de Supervision : une pièce par projet qui a un run, un poste
par étape du pipeline, et autour d'elle des objets dont chacun montre un état
réel de Tessera. Elle **remplace** la vue actuelle sans rien lui retirer : la
vue Liste reste dans le sélecteur pour le détail dense, le clavier et le
lecteur d'écran.

Maquettes (la structure fait foi, les couleurs deviennent des tokens, les
textes d'exemple sont des données — `design/maquette/README.md`) :

- `design/maquette/Bureau.dc.html` — vue normale : pièces, salle de pause,
  salle de réunion, tableau du jour, colonne « À toi », agent choisi ;
- `design/maquette/Bureau-Compact.dc.html` — plus de 6 projets : une rangée
  par projet (pipeline, état, en ce moment, dossiers, courrier, services).

## Règle de conception

**Rien de décoratif.** Un élément qui n'a pas de donnée réelle derrière lui
n'est pas dessiné, même si la maquette le montre. Trois écarts à la maquette
en découlent, listés en fin de document.

## Donnée de l'API pour chaque élément

« Existe » veut dire lu dans le code actuel, pas supposé. Les tickets cités sont
ceux de la section suivante.

| Élément | Donnée qui l'alimente | Manque |
|---|---|---|
| Pièce par projet, poste par étape | `StreamState` du run (`runStore`) : `etape`, `etapesEnCours`, `ticketEvents` (`agent_started`, `agent_done`, `security_audit_*`, `validation_*`). Cinq postes comme la maquette : codeur, testeur, sécurité, reviewer, validateur. Documentation (par lot, ADR-035) et livraison n'ont pas de poste | Piège : `run_closed` remet `etape` à `null` et `etapesEnCours` à `[]` (`streamState.ts`). Les étapes faites d'un run clos se lisent dans `ticketEvents`, jamais dans `etapesEnCours` — sélecteur du ticket-561 |
| Personnage, écran, bulle, pastille | `santeAgent` (`lib/santeAgent.ts`, ticket-549) : `actif`, `attente`, `blocage_suspecte`, `question`, rendus « travaille », « silencieux », « figé ? », « question » | Une file qui attend un merge n'émet rien (`attendre_merge`, `orchestrator.py`) : après 180 s elle se lirait « figé ? ». La santé doit connaître l'attente extérieure — événement du ticket-559, santé du ticket-564 |
| Pièce rangée ou non, contour vert ou rouge | `runClosed`, `issueDuRun` (`en-cours`, `termine`, `bloque`, `erreur`, `autre`), `fermerRuns` de `useSupervision` | — |
| Pile de dossiers | `GET /runs/{run_id}` → `restants` | `restants` d'un run vivant vient de `run.file_restants`, écrit seulement sur `queue_progress` (`run_executor.py`). `FileVivante.ajouter` et `retirer` n'émettent rien : un ticket ajouté par `append` n'apparaît pas — ticket-560 |
| Boîte aux lettres | `livraison_done` (données de `Livraison` : `pr_number`, `arret`, `conflits`, `merged`, `pr_orpheline`), `ci_merge_done` (`merged`, `arret`) ; `GET /projects/{id}/pr-statuses` pour l'état courant après un rechargement. Cinq états : pas de PR, PR ouverte, CI en attente, mergée, refusée | Rien. « CI en attente » = `livraison_done` avec une PR, sans `arret` (ou `pr_orpheline`), tant que `ci_merge_done` n'est pas venu : `orchestrator.py` confie alors la phase 2 au `CIWatcher` |
| Baie de serveur | `GET /projects/{id}/services` (services déclarés, chacun avec son état), `service_output`, `service_closed`, type `ServiceActif` | — |
| Salle de pause | Quota épuisé : événement `error` avec `reason: "quota_exhausted"` et `resume` (`pipeline_outcomes.finish_quota_exhausted`). Le run est alors **clos**, pas suspendu, et `resume` est un libellé déjà formaté. CI de la phase 2 : même dérivation que la boîte aux lettres | `depends_on` : la file suspend sans le dire — ticket-559 (`external_wait`), affiché par le ticket-564 |
| Salle de réunion | Après la résolution : `livraison_done` avec `conflits` non vide, une `pr_number` et un `arret` = conflit résolu, PR à relire (ADR-033) | Pendant la résolution, rien : le résolveur est un callback (`resoudre` dans `livraison.py`) sans événement — ticket-559 (`conflict_resolution`), affiché par le ticket-564 |
| Tableau du jour — dépense | `GET /usage/stats?days=7` → `daily[-1].cost_usd` (chat compris) | Rien. `days=1` est refusé en 422 (`PERIODS = (7, 30, 90)`), donc on lit le dernier point de la série et on ne crée pas de ticket backend. Limite : c'est le jour UTC, pas le jour local |
| Tableau du jour — quota session et semaine | Aucune : `QuotaTracker` naît avec chaque `AgentSdkProvider` (`agent_sdk.py`), garde un seul relevé toutes fenêtres confondues, et n'est diffusé (`quota_updated`) que quand une file s'arrête sur quota bas | Le SDK distingue `five_hour`, `seven_day`, `seven_day_opus`, `seven_day_sonnet`, `overage` (`RateLimitInfo.rate_limit_type`). Un relevé par fenêtre, hors run — ticket-558, affiché par le ticket-565 |
| Colonne « À toi » | Questions : `pendingQuestion` et `expire_a` de `agent_question` (le « 8 min » est réel). Figés : `santeAgent`. PR à relire : ligne « salle de réunion ». Réponse : `supervision.envoyer(runId, { type: "answer" })` | Rien |
| Alerte sonore | Frontend seul : une question arrive (`pendingQuestion` passe de `null` à une valeur) | Voir « Ce qui reste à confirmer » |
| Mode compact | Frontend seul : nombre de projets qui ont un run, supérieur à 6 | — |

## Choix techniques

- **Sprites en SVG inline en pixels** (`rect`, `shape-rendering: crispEdges`),
  comme la maquette, sous `frontend/src/design/bureau/` — même place que
  `design/charts/` (ADR-047). Un canvas se teste mal avec Testing Library et
  n'a pas d'équivalent pour un lecteur d'écran. Chaque poste et chaque objet
  est un `button` avec un `aria-label` qui dit l'état en mots, comme la
  maquette.
- **Coût dans Tauri.** Dix runs × cinq postes × une quinzaine de `rect` font
  quelques centaines de nœuds : le DOM les tient sans effort. Ce qui coûterait
  serait un minuteur par sprite : la vue entière n'a **qu'un** `setInterval`
  de 5 s qui alimente `santeAgent` (seuils de 30 s et 180 s). Le ticket-562
  chiffre le rendu avec dix runs simulés dans un test de rendu. Le plafond de
  2 000 nœuds vient du calcul : une pièce porte cinq postes, chacun un
  personnage, un écran et une bulle d'une quinzaine de `rect`, soit environ
  100 à 150 nœuds, donc 1 000 à 1 500 pour dix pièces. Le plafond laisse une
  marge d'un tiers ; c'est un garde-fou contre une dérive, pas une mesure.
- **Animation** : `transform` et `opacity` seulement (`tape`, `lueur`,
  `flotte`, `vapeur` de la maquette), déclarées en `@keyframes` dans
  `index.css` — pas de `tailwind.config.ts` — et coupées par
  `prefers-reduced-motion`. Sans animation, l'état reste lisible par la bulle
  et la pastille.
- **Couleurs.** Les états n'utilisent que `zinc`, `red`, `amber`, `green`,
  `blue` ; le violet de la chemise est de l'identité, en fond (ADR-026). Les
  tons sans équivalent (peau, cheveux, dossier) sont des jetons `--sprite-*`
  du `@theme`, jamais une famille CSS brute — règle proposée dans
  `contraintes.md`.
- **Une seule source par run.** Le Bureau lit `UseSupervisionResult` comme la
  Liste : même store, mêmes sélecteurs purs. Deux vues d'un même run
  divergeraient, et c'est celle qu'on regarde le moins qui dériverait
  (ADR-034).
- **Découpage.** `components/BureauView/` ; aucun fichier au-dessus de 300
  lignes (plafond du ticket-545). `SupervisionView/index.tsx` fait 266
  lignes : le ticket-567 le **réduit** (la Liste passe dans `ListeView.tsx`, et son test
  la rend directement), il ne l'étend pas. `RunCard`,
  `MenuFermer`, `ServicesLances`, `Chrono` et `issueDuRun` sont repris tels
  quels, pas recopiés.

## Tickets d'implémentation

Aucun ne mêle `backend/` et `frontend/`.

| Id | Titre | Couche | Dépend de |
|---|---|---|---|
| ticket-558 | Un relevé de quota par fenêtre, lisible hors d'un run | backend | — |
| ticket-559 | Une attente extérieure et une résolution de conflit sont annoncées | backend | — |
| ticket-560 | Les tickets restants d'une file vivante comptent les ajouts | backend | — |
| ticket-561 | Les sélecteurs purs du Bureau | frontend | — |
| ticket-562 | Les sprites et la pièce d'un projet | frontend | 561 |
| ticket-563 | Dossiers, boîte aux lettres et baie de serveur | frontend | 560, 562 |
| ticket-564 | Salle de pause, salle de réunion et santé qui sait attendre | frontend | 559, 562 |
| ticket-565 | Le tableau du jour | frontend | 558, 562 |
| ticket-566 | La colonne « À toi » et l'alerte sonore | frontend | 554, 562 |
| ticket-567 | Le Bureau devient la vue par défaut | frontend | 562 à 566 |

Le ticket-555 (quota bas notifié) attendait le ticket backend de quota : il
dépend désormais du ticket-558.

## Ce qui reste à confirmer

- **Le son.** Le ticket-554 fixe « son pour la question et la CI rouge » par
  défaut ; le ticket-550 laissait la valeur « à trancher ». Le propriétaire
  est unique : le réglage « Son » de l'événement « question » du ticket-554.
  Le bouton du Bureau est un second interrupteur sur ce même réglage, jamais
  un second réglage. La valeur par défaut est celle du ticket-554 ; c'est un
  choix de confort, à confirmer par Benjamin.
- **Le seuil du mode compact** (à confirmer par Benjamin, comme le son) compte les projets qui ont un run (vivant ou
  clos, pas rangé). En compact, les projets sans run s'ajoutent en bas, « au
  repos », comme dans la maquette. Hypothèse de lecture de « au-delà de 6
  projets ».

## Écarts à la maquette, par la règle « rien de décoratif »

1. **« Laisser l'agent choisir »** : aucun message du canal n'existe pour cela
   (`answer`, `interject`, `stop` seulement) ; l'agent choisit seul à
   l'échéance (ADR-025). Le bouton n'est pas dessiné ; le compte à rebours,
   lui, l'est.
2. **Le quota** s'affiche « inconnu » tant qu'aucun relevé n'est venu : le SDK
   n'émet un relevé que sur changement d'état. Une barre à 0 % mentirait.
3. **Le jour de la dépense** est le jour UTC : jusqu'à deux heures de décalage
   avec l'heure de Paris.
