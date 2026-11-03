# Compresser le contexte des agents avec headroom — conception

Ticket-589. Statut : **reporter** (ADR-063). Aucune dépendance ajoutée :
headroom n'est pas dans `backend/pyproject.toml` ni `uv.lock`, inchangés ; le
ticket-605 l'a lancé une fois dans un environnement jetable
(`uv run --with headroom-ai`). Tout gain chiffré hors de la section « Mesure »
est une **estimation**. Les chiffres du ticket-605 sont dans les blocs entre
marqueurs de la section 1 et de la section 4, que le script réécrit.

Pages sur lesquelles le ticket s'appuie : le dépôt de headroom
(https://github.com/headroomlabs-ai/headroom), qui annonce 20 à 95 % de tokens
en moins selon le type de données. Ce taux est celui du projet, pas le nôtre ;
rien n'a été rejoué sur des textes de Tessera.

## 1. Ce que Tessera dépense, rôle par rôle

Relevé du 27/10, `GET /api/v1/projects/ide-core/usage/breakdown`, cumul. Les
colonnes « par appel » sont calculées ici (tokens ou coût ÷ appels).

| Rôle | Tokens | Coût | Appels | Tokens / appel | Part du coût |
| --- | ---: | ---: | ---: | ---: | ---: |
| codeur | 680 979 598 | 724,82 $ | 514 | 1,32 M | 65,7 % |
| reviewer | 34 249 077 | 165,89 $ | 406 | 84 k | 15,0 % |
| plan | 27 644 161 | 52,58 $ | 71 | 389 k | 4,8 % |
| securite | 67 801 991 | 43,08 $ | 415 | 163 k | 3,9 % |
| doc-technique | 2 746 929 | 40,34 $ | 311 | 8,8 k | 3,7 % |
| doc-fonctionnelle | 2 560 393 | 35,84 $ | 305 | 8,4 k | 3,2 % |
| architect | 16 253 218 | 29,40 $ | 17 | 956 k | 2,7 % |
| validateur | 2 598 888 | 11,38 $ | 378 | 6,9 k | 1,0 % |
| **Total** | 834 834 255 | 1 103,33 $ | 2 417 | | |

Le testeur n'y figure pas : il lance `scripts/verifier.py` et lit le code de
sortie, il n'appelle pas de modèle. Sa sortie n'atteint un modèle que plafonnée,
par `extract_errors` (5 lignes) et `extract_failure_details` (8 000
caractères), dans `sortie_de_test.py`.

### Ce que le relevé ne dit pas

- **Les tokens du codeur sont surtout du cache lu.** 1,32 M de tokens par appel
  ne sont pas 1,32 M de texte neuf : c'est le contexte de la session, relu à
  chaque tour de la boucle d'outils, facturé au tarif du cache. Le relevé ne
  sépare pas entrée neuve, cache lu et cache créé : `agent_calls` jette
  `cache_creation_tokens` à l'écriture (ticket-604). Sans lui, la part de texte
  compressible du codeur est invisible, et on ne l'extrapole pas.
- **Ce qui compte pour le goulot est le quota, pas les dollars.** On ne sait
  pas non plus comment le quota d'abonnement pondère le cache lu ; les dollars
  ne sont qu'un proxy.
- Le coût par token varie d'un rôle à l'autre (reviewer à environ 4,8 $/M,
  codeur à environ 1,1 $/M) : les dollars suivent le modèle autant que le volume.

### Estimation du gain de headroom

Méthode : *part compressible* du coût (hypothèse, selon le type de contenu que
reçoit le rôle) × *taux de réduction* (hypothèse, fourchette basse du projet,
prise très en dessous de ses 95 %, parce qu'un diff de code est dense). Aucune
des deux valeurs n'est mesurée ; le ticket-605 les mesurera.

| Rôle | Contenu reçu | Part compressible (hyp.) | Taux (hyp.) | Gain estimé |
| --- | --- | ---: | ---: | ---: |
| codeur | lectures de fichiers, sorties de commandes (boucle d'outils) ; **proxy seul** | 20 % | 20-50 % | 29-73 $ — **nul si le cache est cassé** |
| reviewer | diff du run, extraits de tests, lectures de fichiers | 30 % | 20-40 % | 10-20 $ |
| securite | diff du run (le gros du prompt) | 50 % | 20-40 % | 4-9 $ |
| plan | lectures de code | 20 % | 20-40 % | 2-4 $ |
| architect | lectures de code, ADR | 20 % | 20-40 % | 1-2 $ |
| doc-technique | code livré fourni au prompt ; la sortie, non compressible, domine le coût | 25 % | 20-30 % | 2-3 $ |
| doc-fonctionnelle | idem | 25 % | 20-30 % | 2-3 $ |
| validateur | critères + diff ; surtout Ollama, donc **gain en dollars nul** (le délai, peut-être) | — | — | ≈ 0 $ |
| **Total** | | | | **≈ 50-115 $ sur 1 103 $, soit 5-10 %** |

Lecture : deux tiers du gain estimé reposent sur le codeur, donc sur le proxy,
donc sur l'hypothèse la moins vérifiée (section 2). Hors codeur, l'estimation
tient en 21-41 $ cumulés.

### Mesure (ticket-605)

`scripts/mesurer_compression.py` remplit le tableau ci-dessous depuis
`agent_calls` et rejoue headroom sur le diff du run et sur la sortie de
`scripts/verifier.py`. Limites de la méthode : les prompts ne sont pas stockés,
donc « après compression » est une **estimation** (tokens du texte avant et
après, à 4 caractères par token, soustraits de l'entrée mesurée) ; le coût
d'entrée compte le cache créé à 1,25 x le tarif d'entrée, que le calculateur du
backend ignore ; le gain en dollars est pris au tarif d'entrée plein, donc un
plafond. Un run antérieur au ticket-604 n'a pas de `cache_creation_tokens` : il
est « non mesuré ».

Relevé du 28/10 sur `backend/tessera.db`, quatre runs d'ide-core (tickets 604,
576, 574, 589), ouverts en lecture seule. **La base est au `user_version` 8 : la
migration 9 du ticket-604 n'y est pas appliquée** (le backend n'a pas redémarré
depuis le merge), donc la colonne `cache_creation_tokens` n'existe pas et aucun
run n'a d'entrée mesurable. Le premier tableau reste « non mesuré » pour cette
raison, pas faute d'outil. Aucune sortie de test rouge n'a été fournie : les
lignes perdues et le gain en dollars restent « non mesuré ».

<!-- mesure-605:debut -->
| Run | Rôle | Entrée mesurée (tokens) | Après compression (est.) | Lignes perdues |
| --- | --- | ---: | ---: | ---: |
| 64136ccd | tous | non mesuré (colonne cache_creation_tokens absente (migration 9 non appliquée)) | non mesuré (colonne cache_creation_tokens absente (migration 9 non appliquée)) | — |
| fb70a9e9 | tous | non mesuré (colonne cache_creation_tokens absente (migration 9 non appliquée)) | non mesuré (colonne cache_creation_tokens absente (migration 9 non appliquée)) | — |
| e0ee71ce | tous | non mesuré (colonne cache_creation_tokens absente (migration 9 non appliquée)) | non mesuré (colonne cache_creation_tokens absente (migration 9 non appliquée)) | — |
| 1151edb8 | tous | non mesuré (colonne cache_creation_tokens absente (migration 9 non appliquée)) | non mesuré (colonne cache_creation_tokens absente (migration 9 non appliquée)) | — |
<!-- mesure-605:fin -->

Le diff du run, seul, avant et après headroom (indépendant d'`agent_calls`, donc
mesurable même quand le tableau ci-dessus ne l'est pas). Un taux sous 15 % sur
le diff plafonne le gain réel du chemin texte sous 15 % : on ne peut pas retirer
plus de texte qu'on n'en envoie.

<!-- mesure-605-diff:debut -->
| Run | Diff (tokens est.) | Après compression (est.) | Retiré |
| --- | ---: | ---: | ---: |
| 64136ccd | 3 713 | 3 626 | 2.3% |
| fb70a9e9 | 5 815 | 5 743 | 1.2% |
| e0ee71ce | 4 823 | 4 736 | 1.8% |
| 1151edb8 | 4 474 | 4 414 | 1.3% |
<!-- mesure-605-diff:fin -->

`ResultMessage.usage` cumule-t-il les tokens des tours de la boucle d'outils ?
Réponse de `scripts/sonde_usage.py` (un appel réel, deux lectures de fichier) :

<!-- mesure-605-usage:debut -->
`tours=[36805, 40075, 42228] somme=119108 result.usage=119108 -> cumule les tours`
<!-- mesure-605-usage:fin -->

Lecture : trois tours (deux `Read`, puis la réponse) ; chaque valeur est
l'entrée d'un tour (`input_tokens` + `cache_read_input_tokens` +
`cache_creation_input_tokens`). L'`usage` du `ResultMessage` en est la **somme
exacte** : il cumule les tours de la boucle d'outils, il ne rend pas le dernier
seul. Les tokens d'entrée par appel d'`agent_calls` incluent donc chaque relecture
du contexte, ce qui explique les 1,32 M de tokens par appel du codeur (section 1).
## 2. Les trois points d'entrée

Le provider Claude s'appuie sur le CLI embarqué par l'Agent SDK
(`_build_options`, `agent_sdk.py`, qui pose déjà `env` pour le sous-processus).
Une bibliothèque ne s'y branche pas telle quelle.

| | Proxy (`ANTHROPIC_BASE_URL` dans `env`) | Compression du texte avant l'appel | Serveur MCP |
| --- | --- | --- | --- |
| Couvre | tout le CLI, **codeur compris** | diff et extraits de tests mis dans le prompt : reviewer, securite, plan, doc | sorties de l'outil MCP seulement ; pas `Read`, `Bash`, `Grep` natifs |
| Intégration | un processus de plus à lancer, superviser et arrêter, hors `LLMProvider` (ADR-017) | une fonction appelée dans le service appelant, avant `complete` / `stream` | un serveur de plus dans `mcp_servers`, et l'agent doit choisir de l'appeler |
| Perte d'information | sur **tout** le contenu, y compris ce que l'agent s'apprête à éditer | bornée à un texte connu et testable | bornée à ce que l'agent demande |
| Échec fermé (ADR-039) | proxy tombé : les appels échouent, c'est fermé ; proxy qui dégrade : invisible | un garde teste le texte compressé avant l'envoi | l'agent peut ignorer l'outil : aucune garantie |
| Risques propres | voir ci-dessous | un module de compression dans le pipeline | gain non garanti |

Risques propres du proxy, **tous non vérifiés** ici :

1. **Le cache de prompt.** Le codeur relit un long préfixe à chaque tour, au
   dixième du prix. Un proxy qui réécrit d'anciens résultats d'outils change le
   préfixe et fait payer plein tarif ce qui était lu en cache. Le gain annoncé
   sur les tokens peut devenir une perte en dollars et en quota. Headroom dit
   préserver le cache ; ce n'est pas démontré sur nos sessions.
2. **L'authentification d'abonnement.** Le CLI sans `ANTHROPIC_API_KEY` (le
   défaut de Tessera) s'authentifie par la session Claude. Un proxy local
   verrait ce jeton passer, et rien n'établit que le CLI accepte une autre
   base d'URL en mode abonnement. Un jeton qui traverse un composant tiers va
   contre l'esprit d'ADR-053.
3. **Le codeur édite ce qu'il lit.** Un fichier compressé dont une ligne
   manque est un fichier qu'il réécrit faux. Le risque change de nature : on ne
   perd plus un détail de diagnostic, on corrompt un diff.

### Le risque central : le faux verdict

Une ligne `FAILED` tronquée qui laisse passer un `APPROVED`. Tessera borne déjà
la sortie de test (5 lignes, 8 000 caractères), mais elle le fait avec des
extracteurs qui connaissent le format de pytest et de vitest, et que des tests
couvrent. Un compresseur générique n'a pas cette garantie : il doit être
**encadré par la même exigence**, soit chaque ligne `FAILED` et chaque nom de
test de `extract_errors` / `extract_failure_details` survit à la compression.
Un texte compressé qui perd une de ces lignes n'est pas envoyé : on envoie
l'original (la compression échoue du côté de la dépense, jamais du côté du
verdict). Ce garde ne se pose que sur le chemin « texte » ; sur le proxy,
personne ne voit le texte compressé, donc il n'existe pas.

## 3. Tickets d'implémentation

Rien n'est créé à ce stade : la décision est de **reporter**. Les tickets
ci-dessous sont à ouvrir seulement si la section 4 est franchie. Les deux
premiers existent déjà et ne sont pas dupliqués.

**Existants (hors de ce ticket)**

- **ticket-604** — `agent_calls` garde `cache_creation_tokens`. Prérequis de
  toute mesure sur le codeur.
- **ticket-605** — `scripts/mesurer_compression.py`, via
  `uv run --with headroom-ai` (environnement jetable). Produit les chiffres de
  la section 4.

**Conditionnels, numérotation provisoire à partir de 621** (le suivant libre au
moment de l'ouverture)

- **621 — Spike : le CLI embarqué accepte une autre base d'URL en abonnement.**
  Critères : (a) un appel du CLI avec `ANTHROPIC_BASE_URL` vers un proxy
  d'écoute neutre aboutit, ou le ticket dit pourquoi non ; (b) le jeton
  d'abonnement figure-t-il dans les en-têtes vus par le proxy, oui ou non, relevé
  sans être consigné ; (c) sur 20 tours de boucle d'outils identiques, le
  taux de cache lu avec et sans proxy, côte à côte.
- **622 — Une fonction compresse un texte de prompt et refuse la perte.**
  Critères : (a) `compresser(texte, lignes_a_garder)` rend le texte compressé ou
  l'original ; (b) un texte compressé où une ligne `FAILED` manque rend
  l'original (test avec un cas où la ligne manque) ; (c) un compresseur qui
  lève rend l'original et journalise ; (d) aucune dépendance n'est ajoutée sans
  décision écrite dans l'ADR.
- **623 — Interrupteur par rôle dans `agents.json`.** Critères : (a) un champ
  `compression` par rôle, `false` par défaut ; (b) un rôle sans le champ ne
  change pas d'un octet (test sur le prompt envoyé) ; (c) le choix s'écrit une
  fois par run dans `memory/pipeline-log.md`.
- **624 — Reviewer et securite reçoivent le diff compressé.** Dépend de 622 et
  623. Critères : (a) activé, le diff envoyé est plus court ; (b) un diff qui
  touche un fichier de test ou de configuration de test (ADR-027) n'est pas
  compressé ; (c) `agent_calls` montre l'entrée avant/après pour au moins un
  run réel.
- **625 — Le proxy, seulement si 621 conclut positivement.** Critères : un
  processus lancé et arrêté par le backend sur un port libre, qui ne tue jamais
  un processus existant ; un proxy tombé met le run en `blocked` (ADR-037),
  jamais en repli silencieux sur l'API directe ; un projet ou un rôle
  l'active explicitement (le défaut protège).

## 4. Recommandation et seuil de réouverture

**Reporter.** Pas écarter : mesurer ne coûte presque rien (604 puis 605), et
l'estimation haute est non négligeable. Pas adopter : le plus gros poste, le
codeur, n'est atteignable que par un proxy dont on ignore s'il fonctionne en
abonnement et s'il préserve le cache ; et la partie sûre du gain (hors codeur)
tient en 21-41 $ cumulés sur 1 103 $, trop peu pour ajouter une dépendance et
un chemin qui touche un verdict.

Si le sujet est rouvert, le point d'entrée visé est la **compression du texte
avant l'appel**, limitée à reviewer et securite : elle reste dans
`LLMProvider`, se teste, et son garde échoue du côté de la dépense. Le proxy ne
s'envisage qu'après le spike 621.

**Seuil, que le ticket-605 applique à ses mesures** (au moins deux runs réels,
dont un avec un tour de test rouge) :

1. *Chemin texte* — rouvrir si, sur reviewer et securite, headroom retire **au
   moins 15 % du coût d'entrée mesuré** (soit environ 31 $ des 209 $ cumulés),
   **et** perd **zéro** ligne `FAILED` ou nom de test.
2. *Chemin proxy* — rouvrir seulement si `cache_creation` + `input` du codeur
   pèsent **au moins 25 %** de ses tokens (ticket-604) **et** le spike 621
   montre le CLI fonctionnel en abonnement **et** un taux de cache lu qui ne
   baisse pas de plus de 5 points.
3. Une seule ligne perdue, sur n'importe quel run, ferme le chemin texte
   jusqu'à nouvelle décision.

Ce qu'on ne tranche pas ici : l'acceptation d'un composant tiers sur le chemin
du jeton d'abonnement, si le spike 621 le montrait fonctionnel. C'est une
décision de confiance, elle revient à l'humain.

### Conclusion des mesures

<!-- mesure-605-conclusion:debut -->
**Conclusion du ticket-605 : reporter.** headroom retire au plus 2.3% du diff, sous 15% : plafond du gain du chemin texte ; part d'entrée du codeur non mesurée. Chiffres : 4 run(s) mesuré(s), gain texte non mesuré, taux sur le diff seul 2.3%, lignes perdues non mesuré, part d'entrée du codeur non mesurée.
<!-- mesure-605-conclusion:fin -->

Application du seuil (section 4) aux chiffres du 28/10 :

- *Chemin texte* : headroom retire 1,2 à 2,3 % du diff sur quatre diffs réels,
  loin des 15 % requis. Le diff est le gros du prompt de securite et une part de
  celui du reviewer ; on ne retire pas plus de texte qu'on n'en envoie, donc le
  gain réel du chemin texte est sous 15 % : **fermé**. Réserve :
  le plafond porte sur le diff ; les extraits de test du reviewer ne sont pas
  rejoués (pas de sortie rouge fournie), et la perte de lignes `FAILED` n'a pas
  été éprouvée.
- *Chemin proxy* : **non mesuré**. Il faut appliquer la migration 9 (redémarrer
  le backend), laisser tourner des runs, puis relancer le script ; le spike 621
  reste de toute façon une condition.
- D'où **reporter** : le chemin texte, la partie sûre, ne vaut pas la peine ; le
  chemin proxy ne peut pas être jugé sans la colonne du ticket-604. Rien n'est
  écarté tant que la part d'entrée du codeur est inconnue.

Pour compléter : après redémarrage du backend et deux nouveaux runs, relancer
`scripts/mesurer_compression.py --ecrire` avec `--sortie-test` et `--run-rouge`
(sortie de `scripts/verifier.py` sur un worktree jetable portant un test rouge).
