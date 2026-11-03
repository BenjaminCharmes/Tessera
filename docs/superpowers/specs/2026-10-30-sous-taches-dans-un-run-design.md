# Des sous-tâches dans un run — conception

Ticket-668. Décision : ADR-066. Spec écrite le 30/10/2026, sans code.

**Recommandation : écarter.** Un run garde un diff, un commit et une revue par
tour. Les sous-tâches ne raccourcissent que l'étape du codeur, la plus petite
des trois, et multiplient les coûts fixes des deux autres. On mesure d'abord
ce qu'on ne voit pas aujourd'hui : l'épuisement des actions du codeur
(ticket-702).

## 1. Ce que le journal mesure

Source : `memory/pipeline-log.md`, relevé du 30/10. Chaque nombre vient d'un
`Grep` sur le journal ; rien n'a été rejoué.

| Mesure | Valeur |
| --- | --- |
| Runs approuvés (`APPROVED après N tour(s)`) | 358 |
| Tours renvoyés au codeur pour tests rouges | 118 (0,33 par run) |
| Refus de revue (`CHANGES_REQUESTED tour N`) | 105 (0,29 par run) |
| … dont portés par le reviewer / par le validateur | 35 / 46 (24 d'un autre libellé) |
| Runs arrivés à un tour 3 depuis le 20/10 | 16 |
| Tour 1 du codeur, 40 runs (tickets 563 à 575) | médiane 204 s, p90 497 s, de 33 à 697 s |
| Tour 1 du codeur, maxima relevés | 950 s (tickets 611 et 614) |
| Retour du codeur après refus (5 tours) | médiane 97 s |
| Passe de tests complète | 462 à 500 s (tickets 610, 612, 614) |
| Passe de tests ciblée (ticket-615) | ≈ 147 s |
| Audit sécurité par tour (7 tours) | médiane 109 s |
| Validateur par tour (7 tours, reviewer en parallèle dedans) | médiane 283 s |
| Run complet, tickets 610 à 615 | 21, 33, 31, 29, 43, 27 min ; médiane 30 |

Deux écarts avec le ticket. Les « 45 minutes dont 27 de tests » ne se
retrouvent pas dans le journal du 28/10 : la passe complète y dure 8 min, une
fois ou deux par run ; le reste d'un ticket de 45 minutes est ailleurs
(livraison, CI). Et **« un gros ticket épuise les actions du codeur » n'est
pas observable** : `agent_sdk.py` (lignes 428-464) lit `total_cost_usd`, les
tokens et `session_id` du `ResultMessage`, jamais `num_turns` ni `subtype`.
La documentation du SDK dit que l'épuisement rend `subtype ==
"error_max_turns"` et `is_error == True`
(https://code.claude.com/docs/en/agent-sdk/python). Le travail partiel part
alors aux tests comme un travail fini, sans trace.

### Modèle d'un ticket

Médianes ci-dessus, probabilités du tableau : C = 3,4 min (tour 1 du codeur),
T = 7,7 min (passe complète), A = 1,8 + 4,7 = 6,5 min (sécurité, puis
validateur avec le reviewer en parallèle), R = 1,6 min (retour du codeur).

`durée = C + (1 + 0,33)·T + (1 + 0,29)·A + (0,33 + 0,29)·R`
`= 3,4 + 10,2 + 8,4 + 1,0 ≈ 23 min`

Le codeur en pèse 19 % (4,4 min), les tests 45 %, l'audit 36 %. Le modèle
tombe sous la médiane observée (30 min sur 610-615) parce que ces six tickets
sont plus gros que la moyenne ; l'ordre de grandeur tient.

Coût, par appel (relevé du 27/10, spec `2026-10-27-compression-contexte`) :
codeur 1,41 $, reviewer 0,41 $, sécurité 0,10 $, validateur 0,03 $, plan
0,74 $. Un ticket moyen : 1,62 appels de codeur + 1,29 de chacun des autres
≈ **3,0 $** (estimation à partir des appels, le journal ne porte pas de
dollars).

## 2. Les trois formes

Pour chaque forme, N = 3 sous-tâches. `F` = coût fixe d'une session de codeur
(lecture du ticket, des ADR, de la carte) ≈ 1,5 min : 9 tours 1 sur 40 durent
moins de 111 s, ce que coûte une session qui ne fait presque rien.

### A. Sous-tâches tirées du plan (`plan: true`)

Le plan est du texte libre (`run.plan`, `pipeline_plan.run_plan`) et son
échec est toléré : « s'il échoue, le run continue sans lui ». Des sous-tâches
tirées de lui auraient une forme de run qui dépend d'une aide optionnelle :
un plan en échec ferait basculer le run, sans le dire, vers un seul tour.
Il faudrait aussi un plan structuré (schéma, ADR-061) ou un second appel.
Seuls les tickets `plan: true` en profiteraient : 71 appels de plan pour 514
de codeur. Même effet que B sur la durée et le coût, plus 0,74 $ et un appel
qui n'existe pas toujours. **Écartée.**

### B. Sous-tâches écrites dans le ticket

Une section `## Sous-tâches` que le planificateur ou l'humain écrit, que le
validateur lit avec le ticket, déterministe à parser. C'est la meilleure des
deux formes à sous-tâches ; voici ce qu'elle coûte, variante par variante.

| Variante | Durée | Coût |
| --- | --- | --- |
| B1 — codeur par sous-tâche, tout le reste une fois | + (N−1)·F = **+ 3,0 min** | + 0,8 à 1,4 $ (codeur) |
| B2 — B1 + reviewer après chaque sous-tâche | B1 + 3 × 0,4 min − gain | B1 + 0,57 $ |
| B3 — B2 + sécurité et validateur par sous-tâche | B2 + 2 × 6,5 = **+ 13 min** | + 0,26 $ de plus, +13 min |

- Coût du codeur : appel de sous-tâche = 1,41 × (φ + (1−φ)/3), φ part fixe
  de l'appel entre 0,3 et 0,5, soit 2,25 à 2,82 $ pour trois contre 1,41 $.
  C'est une borne haute : des sessions plus courtes relisent un contexte plus
  petit à chaque action, et c'est la seule voie par laquelle le coût du
  codeur (66 % du total) pourrait baisser. Le journal ne dit pas de combien.
- Gain de B2 : un refus du reviewer attrapé dans la sous-tâche coûte
  R + 0,4 = 2 min au lieu d'un tour entier T + A = 14,2 min. Le reviewer porte
  35 refus sur 105, donc au mieux 0,29 × 0,33 × 12,2 ≈ **1,2 min** par run.
  Les 46 refus du validateur jugent des critères de ticket : aucune
  sous-tâche ne les voit. Les 118 tests rouges se découvrent à la passe finale
  dans toutes les formes ; ils reviennent au codeur comme aujourd'hui.
- Total B2 : + 3,0 + 1,2 − (≤ 1,2) = **+ 3 à + 4 min** (+13 à 18 % sur 23) et
  **+ 1,4 à + 2,0 $** (+ 47 à 66 % sur 3,0 $). Plus lent et plus cher, pour
  un gain qui ne vaut que si les refus se règlent localement.
- Les tests « une seule fois après la dernière » ne changent rien : le
  pipeline lance déjà les tests une fois par tour, après le codeur.

### C. Statu quo, tickets plus petits

Le planificateur découpe déjà les lots. Un ticket de plus coûte ses coûts
fixes : T et A, soit ≈ 14 min et ≈ 0,54 $, plus une session de codeur. C'est
plus cher que B1 (3 min) pour la même coupure. C'est aussi la seule forme
dont le résultat se relit : un ticket a sa PR, son CI, ses critères. Elle ne
change aucun code.

## 3. Ce que B ferait au code

Ces faits écartent les variantes à commit par sous-tâche, même si la
décision venait à rouvrir.

- **ADR-018.** `finish_approved` fait un commit unique, `commit_work` →
  `commit_all(message)`. Un commit par sous-tâche demande un message par
  sous-tâche et un état de run qui les distingue. Le dépôt cible squashe la
  PR vers `develop` : ces commits disparaissent au merge. Leur seule valeur
  serait un point de reprise.
- **`approved_sha`** (ticket-492) vaut pour le dernier commit : inchangé si
  seuls les commits de rangement le suivent, mais les commits de sous-tâches
  le précèdent, et `CIWatcher` n'a rien à en savoir.
- **Reprise** (`verifier_travail_repris`, ticket-497). Elle compte
  `commits_repris` et lance les tests sur la branche. Sur une branche à moitié
  faite, les tests sont rouges et le codeur repart « en premier » sans savoir
  quelles sous-tâches sont finies. Il faudrait un marqueur d'avancement
  persistant, relu par la reprise et par `refus_precedent`, un contrat de plus
  entre le journal et le pipeline.
- **Ce que voient reviewer et validateur.** `_capture_diff(orch, run, prose)`
  calcule un diff unique de la branche contre sa base ; `run.reviewed_code`
  est lu en quatre endroits de `pipeline_stages.py`. Relire une sous-tâche
  demande une base de diff en paramètre. Le validateur, lui, doit rester sur
  le diff cumulé : ses critères sont ceux du ticket.
- **Événements et UI.** Les événements d'agent portent `round` et le fil du
  run (`FilDuRun`) le lit pour ranger les étapes par tour. Une sous-tâche
  ajoute un second axe aux événements, au fil et au journal, que rien ne
  porte aujourd'hui.
- **`LLM_MAX_TURNS`.** 30 par appel de codeur (`config.llm_max_turns`) ; N
  sous-tâches donneraient N × 30 actions, sans autre frein que
  `llm_max_budget_usd` par appel et le plafond de dépense du ticket
  (`ticket_budget_exhausted`, vérifié au tour 2 seulement). Le plafond
  d'actions ne se lève pas en découpant : il se déplace.
- **`max_review_rounds`.** Un refus dans une sous-tâche compterait-il comme un
  tour ? Aucune réponse ne va de soi, et ce serait à décider avant tout code.

## 4. Pourquoi écarter, et à quel signal rouvrir

L'idée résout un problème dont on n'a pas la preuve (l'épuisement des
actions) en touchant l'étape qui pèse 19 % de la durée. Les 81 % restants se
paient par diff, pas par ligne : une sous-tâche relue les paie plusieurs fois
(B3) ou ne les touche pas (B1, B2).

Rouvrir quand l'un des deux seuils tombe, relevé par `Grep` sur le journal :

- sur 30 runs consécutifs, **10 %** des appels de codeur finissent sur
  `error_max_turns` (mesure du ticket-702) ;
- le p90 du tour 1 du codeur dépasse **12 min** (497 s aujourd'hui).

Si l'un tombe, la forme à rouvrir est **B1**, et seulement elle : sections
`## Sous-tâches` du ticket, une session de codeur par sous-tâche dans le même
worktree, **aucun commit intermédiaire** (ADR-018 et `approved_sha` restent
intacts), pas de revue par sous-tâche, tests, audit et validateur une fois.
Coût attendu : + 3 min, + 1 $ environ.

## 5. Tickets qui en découlent

- **ticket-702 — The codeur's exhausted turns are recorded and journalised.**
  Rend le premier seuil mesurable. Critères dans la fiche.

Pas d'autre ticket : aucune règle nouvelle, donc rien sous `## Proposées`.

## 6. Ce que cette spec ne tranche pas

- Les refus classés « autre libellé » (24 sur 105) ne sont pas répartis entre
  reviewer et validateur.
- `φ` (part fixe d'un appel de codeur) et l'effet de la longueur de session
  sur les tokens ne sont pas mesurés ; le coût de B est une fourchette.
- Un tour 1 de 950 s (tickets 611 et 614) est-il un ticket trop gros ou un
  tour lent ? Le journal ne le sépare pas. Le ticket-702 en donnera la moitié.
