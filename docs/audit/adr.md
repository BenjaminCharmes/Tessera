# Audit des ADR — statut, doublons, contradictions

État au 2026-10-29 : ADR-001 à ADR-065 (ADR-016 est dans `decisions-archive.md`).
Lu dans le texte de chaque ADR, pas copié de `memory/adr-audit.md` (qui s'arrête
à ADR-051, état du 02/10).

## Ce que l'audit établit en une page

- Sur 65 ADR : **56 en vigueur, 8 historiques, 1 remplacée** (ADR-016 par ADR-040).
  Dix-huit en vigueur portent un amendement ou un complément d'un autre ADR.
- Il y a **deux règles fausses en vigueur dans `contraintes.md`**, donc dans chaque
  appel d'agent : le verdict reviewer « par mot-clé » (ADR-009) et « seule une
  indisponibilité déclenche le repli » (ADR-046, complétée par ADR-059).
- **Trois règles citent un ADR qui ne contient pas leur contenu** : le script de
  `test_command`, `approved_sha`, et la règle « hors de la racine » qui ignore
  ADR-056.
- **Trois ADR sans portée n'atteignent aucun agent** : ADR-054, 059, 060. Rien ne
  les cite dans `contraintes.md`, et `adr-audit.md` ne va pas jusqu'à eux : le test
  de traçabilité ne les voit pas.
- **Le skill `write-adr`, le skill `code-review` et `projects/ide-core/CLAUDE.md`
  décrivent une injection de `decisions.md` qui n'existe plus** (voir « Doublons et
  contradictions », paire 3).

## 1. Statuts

Vocabulaire : **en vigueur** (guide encore une décision), **historique** (le fait
reste vrai, ne guide plus rien), **remplacée** (un autre ADR dit autre chose ; elle
s'archive). « Amendée par » ne retire pas le statut « en vigueur » : l'ADR reste
lue avec celle qui l'amende.

Écart avec `adr-audit.md` : ADR-009 (« règle » → en vigueur, texte réécrit),
ADR-032, 034 et 035 (« histoire » → en vigueur : chacune guide encore un architecte ;
la portée `architect` dit qui la lit, pas si elle est vivante).

| ADR | Titre | Statut | Remplacée par | Amendée / complétée par | Note |
|-----|-------|--------|---------------|-------------------------|------|
| 001 | Self-hosting | historique | — | — | principe fondateur |
| 002 | Pas de framework agent externe | historique | — | — | |
| 003 | Tickets en Markdown | historique | — | — | |
| 004 | Tauri plutôt qu'Electron | historique | — | — | |
| 005 | uv | historique | — | — | |
| 006 | `ProjectLoader` filtre sur `CLAUDE.md` | en vigueur | — | — | |
| 007 | `name` depuis le H1 | en vigueur | — | — | |
| 008 | Orchestrateur sans état | en vigueur | — | 038, 056 | « même arbre » devenu « même base » |
| 009 | Verdict reviewer | en vigueur | — | 061 | réécrite en place le 28/10 (ticket-614) ; le mot-clé qu'elle posait n'existe plus |
| 010 | github-sync dans `/agents/run` | en vigueur | — | — | |
| 011 | httpx plutôt que PyGitHub | historique | — | — | |
| 012 | Monaco bundlé | en vigueur | — | — | |
| 013 | Pas d'état global | en vigueur | — | — | à réexaminer (paire 7) |
| 014 | Vitest + RTL | en vigueur | — | — | |
| 015 | CI en jobs parallèles | historique | — | 050 | « cinq jobs » faux : `ci.yml` en compte six |
| 016 | Scope fs Tauri `$HOME` | remplacée | 040 | — | archivée |
| 017 | `LLMProvider` | en vigueur | — | — | |
| 018 | Une branche, un commit par run | en vigueur | — | 051 | |
| 019 | Le chat commite | en vigueur | — | — | |
| 020 | Deux plafonds | en vigueur | — | — | |
| 021 | `.git/info/exclude` | en vigueur | — | 023 | |
| 022 | Push sans force, PR | en vigueur | — | 029 | texte déjà corrigé (paires examinées) |
| 023 | Mode artefacts fermé | en vigueur | — | — | |
| 024 | Projet = racine de son dépôt | en vigueur | — | 028, 056 | |
| 025 | Question sans réponse | en vigueur | — | 041 | transport seul |
| 026 | Cinq familles de couleurs | en vigueur | — | 047 | amendée en place le 30/09 |
| 027 | Pas d'historique git | en vigueur | — | — | étendue sans ADR (règle 7) |
| 028 | `git_root: ancestor` | en vigueur | — | 056 | |
| 029 | Autonomie par projet | en vigueur | — | 033, 045 | |
| 030 | La livraison ne fait pas échouer le run | en vigueur | — | 051 | |
| 031 | Écriture sous la racine | en vigueur | — | 053, 056 | |
| 032 | Un ADR déclare qui il contraint | en vigueur | — | — | décrit le chemin `decisions.md`, devenu repli |
| 033 | Un conflit se tente, se relit | en vigueur | — | — | |
| 034 | Une règle, un endroit | en vigueur | — | — | |
| 035 | Doc par lot | en vigueur | — | 057 | |
| 036 | Clef de manifeste renommée | historique | — | — | gardée par test |
| 037 | Une panne ne perd pas le travail | en vigueur | — | — | |
| 038 | Un run à la fois | en vigueur | — | 051, 056 | |
| 039 | Une porte qui n'a pas jugé refuse | en vigueur | — | — | |
| 040 | Shell sans porte vers le disque | en vigueur | — | — | remplace 016 |
| 041 | Un run est observé | en vigueur | — | — | |
| 042 | Services déclarés | en vigueur | — | — | |
| 043 | Rien de pro dans un dépôt perso | en vigueur | — | — | |
| 044 | Ce qu'une machine lit, en anglais | en vigueur | — | — | |
| 045 | Dépôt sans CI | en vigueur | — | — | |
| 046 | Provider par rôle | en vigueur | — | 059 | règle de `contraintes.md` périmée (paire 1) |
| 047 | Palette des graphiques | en vigueur | — | — | |
| 048 | Termes interdits avant push | en vigueur | — | 050 | |
| 049 | Rôle web sans shell | en vigueur | — | — | |
| 050 | Termes interdits, trois portes | en vigueur | — | — | |
| 051 | Libérer l'arbre après la PR | en vigueur | — | 060, 065 | |
| 052 | Journal / contraintes séparés | en vigueur | — | — | texte au futur, chiffres périmés (paire 6) |
| 053 | Jetons hors du backend | en vigueur | — | — | amende 031 |
| 054 | Proposer des tickets (worktree) | en vigueur | — | — | aucun agent ne la reçoit |
| 055 | Règle commune sous « Proposées » | en vigueur | — | — | |
| 056 | Un run, son worktree | en vigueur | — | — | amende 028, 031 |
| 057 | Doc lue dans le code livré | en vigueur | — | — | amende 035 |
| 058 | Le Bureau remplace Supervision | en vigueur | — | 064 | |
| 059 | Run « rapide » | en vigueur | — | — | complète 046 ; aucun agent ne la reçoit |
| 060 | Un ticket non mergé | en vigueur | — | — | complète 051 ; aucun agent ne la reçoit |
| 061 | Verdict en JSON validé | en vigueur | — | — | texte au futur (paire 5) |
| 062 | Contrôle visuel | en vigueur | — | — | |
| 063 | Reporter la compression | en vigueur | — | — | report, pas règle de comportement |
| 064 | Fichier d'activité | en vigueur | — | — | complète 058 |
| 065 | Livraison attend le watcher | en vigueur | — | — | complète 051 |

## 2. Doublons et contradictions

Chaque paire cite une phrase de chaque ADR, recopiée de `decisions.md` ou
`contraintes.md`.

### Contradictions réelles

**Paire 1 — ADR-046 / ADR-059, et la règle de `contraintes.md`.**
- ADR-046 : « Seule une **indisponibilité** — connexion refusée, délai, modèle
  absent — déclenche le repli ».
- ADR-059 : « un second déclencheur du repli : le choix explicite, au lancement ».
- `contraintes.md` : « Seule une indisponibilité déclenche le repli », avec ADR-046
  pour seule référence. La règle injectée nie un déclencheur que le produit a.

**Paire 2 — règle ADR-009 de `contraintes.md` / ADR-009 / ADR-061.**
- `contraintes.md` : « Le verdict reviewer se parse par mot-clé ».
- ADR-009 : « L'orchestrateur ne lit plus le texte du reviewer ».
- La section « Proposées » dit de la règle de remplacement : « quand le reviewer est
  livré ». Il l'est (`services/reviewer_schema.py`, ticket-614). Le reviewer reçoit
  donc deux consignes opposées.

**Paire 3 — injection de `decisions.md`.**
- ADR-055 : « `decisions.md` n'est pas concerné : il n'est injecté nulle part ».
- Skill `write-adr` : les routeurs « injectent `memory/decisions.md` dans le contexte
  projet de **chaque** appel d'agent » (sa description dit « injected whole »).
- `adr.py`, vrai des deux : « Si `contraintes.md` est absent, on retombe sur
  `decisions.md` ». Les quatre routeurs passent par `lire_contraintes`.
- Réalité : sur ide-core, `decisions.md` n'est lu par aucun agent ; sur un projet
  importé **sans** `contraintes.md`, il est injecté, filtré par portée. Le skill est
  faux pour ide-core et juste ailleurs ; ADR-055 est juste pour ide-core seulement.
- Même erreur : `projects/ide-core/CLAUDE.md` (« Importé lui aussi, donc déjà en
  contexte ») et le skill `code-review` (« part dans chaque appel d'agent »). Aucun
  `@`-import ne charge `decisions.md`.

**Paire 4 — ADR-032 / la pratique.**
- ADR-032 : « Elle ne s'écrit que sur un ADR qui enregistre un choix passé, jamais
  sur une contrainte de comportement ».
- ADR-026 : « **Portée** : codeur, reviewer », sur une contrainte de comportement
  (les couleurs). Idem ADR-041, 006, 007, 008, 010, 012, 013, 014.
- Dans `contraintes.md` la portée est portée par la **règle** (`*(codeur, reviewer)*`)
  et dit qui doit obéir ; dans `decisions.md` elle devait dire qui peut rediscuter.
  Les deux sens coexistent, et `test_adr_pertinents.py` ne verrouille que ses deux
  listes explicites (`_CONTRAINTES`, `_CHOIX_PASSES`), qui omettent ces ADR.

### Textes périmés (contradiction avec l'état du dépôt)

**Paire 5 — ADR-009 / ADR-061.**
- ADR-009 : « amendé 2026-10-28, ticket-614 ».
- ADR-061 : « ADR-009 est amendée à la livraison du reviewer » (futur).
- De plus les deux décrivent le même seuil : ADR-009, « Un `CHANGES_REQUESTED` dont
  **toutes** les remarques sont sous `reviewer_confidence_threshold` » ; ADR-061,
  « `APPROVED` avec une remarque au-dessus du seuil refuse ». Deux descriptions
  d'une règle (ADR-034).

**Paire 6 — ADR-052.**
- ADR-052 : « Les agents liront `contraintes.md` à la place du journal une fois
  ticket-311 livré » ; « le journal fait 43 Ko et 51 ADR ».
- ticket-311 est dans `tickets/done/` ; le journal compte 64 ADR.

**Paire 7 — ADR-013 / ADR-058.**
- ADR-013 : « L'état partagé (projet actif, ticket actif) tient dans
  `useActiveProject` ».
- ADR-058 s'appuie sur « le store de run » ; `frontend/src/hooks/runStore.ts` existe,
  en `useSyncExternalStore`. Ni Zustand ni Jotai : le refus d'ADR-013 tient, sa
  condition littérale non. Trois fichiers de `hooks/` utilisent
  `useSyncExternalStore`, sous le seuil de cinq que fixe ADR-013.

**Paire 8 — ADR-015 / ADR-050.**
- ADR-015 : « cinq jobs ».
- ADR-050 : « job requis par la protection des branches » ; `ci.yml` déclare six
  jobs, dont `termes-interdits`.

### Doublons (même règle décrite deux fois)

**Paire 9 — ADR-018 / ADR-037 / ADR-038.**
- ADR-018 : « finit toujours par un commit ».
- ADR-037 : « commite le travail écrit sous ».
- ADR-038 : « Chaque sortie du pipeline commite ».
- Trois ADR restent distinctes (échec de commit, exception, verrou), mais la phrase
  d'origine est répétée trois fois. `contraintes.md` en garde deux.

**Paire 10 — ADR-043 / ADR-048 / ADR-050.**
- ADR-043 : « La règle porte sur le contenu **et** sur les métadonnées git ».
- ADR-048 : « contrôle les lignes ajoutées du diff, les messages de commit et les
  auteurs contre `FORBIDDEN_TERMS` ».
- ADR-050 : « est contrôlé au push du pipeline, par un hook `pre-push` en manuel,
  et en CI ».
- ADR-050 redit la porte d'ADR-048 puis en ajoute deux. `contraintes.md` a deux
  puces qui se recouvrent (« Avant tout push… » et « trois portes »). ADR-048 rejetait
  un « hook pre-push global — ignoré pendant les runs (ADR-027) » ; ADR-050 en ajoute
  un **en plus** : pas de contradiction, la porte du pipeline reste.

**Paire 11 — ADR-021 / ADR-023.**
- ADR-021 : mode `local`, exclusion par `.git/info/exclude`.
- ADR-023 : « ADR-021 posait le mécanisme mais le faisait dépendre d'une
  déclaration ». Une suite, pas un doublon : ADR-023 doit seulement être marquée
  comme complétant ADR-021.

### Paires examinées, à ne pas corriger

- **ADR-008 / ADR-038** : ADR-008 dit « « zéro lock » ne vaut qu'**entre**
  projets » et renvoie à ADR-038. Déjà résolue dans le texte ; reste le vocabulaire
  « même arbre », que ADR-056 réécrit : `"même arbre" (ADR-038) devient "même base"`.
- **ADR-022 / ADR-029** : ADR-022 dit « Le merge, lui, ne s'interdit plus
  partout ». Déjà amendée dans le texte, sans le marqueur « amendé par ».
- **ADR-039 / ADR-062** : ADR-062, « `joindre` : un échec se journalise » et
  « Aucun modèle ne les juge » ; ADR-039 vise « l'audit sécurité et la validation ».
  La capture n'est pas une porte en `joindre` ; en `relire`, ADR-062 cite ADR-039.
  Compatibles.

## 3. Règles de `contraintes.md`

Chaque règle est rattachée à l'ADR qu'elle cite. Aucune ne cite une ADR
historique ou archivée. Le défaut tient à ce que les règles disent, pas à ce qu'elles
citent.

| Règle (début) | ADR citée(s) | Verdict |
|---|---|---|
| « Le verdict reviewer se parse par mot-clé » | 009 | **périmée** : 009 et 061 disent l'inverse (paire 2) |
| « Seule une indisponibilité déclenche le repli » (règle provider) | 046 | **périmée** : 059 ajoute un déclencheur (paire 1) |
| « Le script que `test_command` lance se refuse en écriture » | 027 | **ADR muette** : 027 ne parle ni de `test_command` ni de la configuration de test |
| « Une approbation vaut pour un commit précis » | ticket-492, 039 | **sans ADR** : 039 ne dit rien d'`approved_sha` |
| « Ne jamais écrire hors de la racine du projet » | 031, 053 | **incomplète** : 056 change la racine (elle est dite dans la règle d'à côté) |
| « Un projet ne porte qu'un run à la fois » | 038 | juste : 056 remplace « arbre » par « base », la règle dit « projet » |
| « Pas de gestionnaire d'état global… `useActiveProject` » | 013 | **à réexaminer** (paire 7) |
| Quatre propositions (061, 062, 064, 065) | 061/009, 062, 064/058, 065/051 | non injectées ; la 1re **doit** être acceptée (paire 2) |
| Autres règles | en vigueur | conformes au texte de l'ADR |

ADR en vigueur, **sans portée**, **absentes** de `contraintes.md` : 054, 059, 060.
Le skill `write-adr` dit qu'un ADR sans portée « part à tous » ; ce n'est vrai que
par `decisions.md`, qu'aucun agent ne lit sur ide-core. Appliquée à la lettre, la
question de la portée (« un agent qui ne la lit pas peut-il mal se comporter ? »)
répond **non** pour ces trois : elles décident du fonctionnement du backend. Elles
relèvent donc de la portée `architect` (liste `_CHOIX_PASSES`), pas d'une ligne de
`contraintes.md`.

## 4. Forme proposée

Trois options :

- **A. Une ligne `**Statut**` par ADR, source unique ; archive réservée aux
  remplacées.** *Recommandée.*
- B. A, plus archive des 8 historiques.
- C. Un tableau seul (l'état de `adr-audit.md`), sans toucher `decisions.md`.

**Recommandation : A.**

Pourquoi pas C : le tableau est une seconde description du statut, il a déjà dérivé
(arrêté à 051). ADR-034 : une règle, un endroit.

Pourquoi pas B : `decisions-archive.md` se définit comme « les ADR qui ne contraignent
plus rien… ou qu'un ADR postérieur a explicitement remplacés ». Un historique vrai ne
remplit pas cette définition. L'archiver casserait de surcroît
`test_les_choix_passes_portent_une_portee` (ADR-001, 003, 036 doivent rester dans
`decisions.md`), et ADR-052 appelle `decisions.md` « le journal complet ». Aucun
gain de tokens : sur ide-core, aucun agent ne lit le fichier.

Forme de la ligne, sous `**Date**` : `**Statut** : en vigueur` ;
`**Statut** : en vigueur — amendée par ADR-051` ;
`**Statut** : remplacée par ADR-040`. Tests : `_PORTEE` ne lit que `**Portée**`,
`_DEBUT_ADR` que `## ADR-` : la ligne ne les gêne pas. **Coût** : 4 à 8 mots par ADR,
soit environ 400 mots pour 65, comptés dans les 160 de chaque ADR : le test de budget
dit lesquelles sont à la limite. Zéro token sur ide-core ; sur un projet importé qui
retombe sur `decisions.md`, quelques tokens par ADR qui part.

Contraintes à respecter par le ticket qui l'implémente :
- `test_consignes_coherentes.py::_audit_classement` ne lit `adr-audit.md` qu'avec les
  mots `règle|fusion|histoire|obsolète` ; aucun fichier nouveau ne doit reprendre ce
  format de tableau.
- `adr-audit.md` disparaît **dans le même ticket** que la lecture du statut depuis
  `decisions.md`. Correspondance : en vigueur ↔ règle, historique ↔ histoire,
  remplacée ↔ obsolète. « Fusion » n'est employé nulle part.
- `test_tout_adr_cite_existe_encore` lit déjà l'archive : aucun changement.
- `decisions-archive.md` ne s'importe nulle part (test existant).
- Les numéros d'ADR ne se réattribuent pas (ticket-659 les alloue par code).

## 5. Tickets de correction

Pas de numéros : ils s'allouent à la création (ticket-659). Chacun est indépendant du
suivant sauf mention. « À la main » : un run ne peut pas écrire là (ADR-055 pour
`contraintes.md`, ticket pour `.claude/` et `CLAUDE.md`).

**C1 — Une ligne `**Statut**` par ADR (`decisions.md`, backend).**
- `grep -c "^\*\*Statut\*\*" decisions.md` = `grep -c "^## ADR-" decisions.md`.
- Chaque valeur est `en vigueur`, `historique` ou `remplacée par ADR-NNN` ; l'ADR
  citée existe dans `decisions.md` ou l'archive ; le tableau de ce document sert de
  référence.
- Un test refuse un ADR sans `**Statut**`, ou à vocabulaire inconnu, ou « remplacée »
  qui ne vise rien.
- `test_aucun_adr_ne_depasse_le_budget` passe.

**C2 — Corriger les textes périmés des ADR (`decisions.md`).**
- ADR-052 : plus de « liront », plus de « 43 Ko et 51 ADR » ; la décision dit que
  `contraintes.md` est lu seul, `decisions.md` en repli seulement.
- ADR-061 : plus de « à la livraison du reviewer ».
- ADR-015 : plus de « cinq jobs » (six, dont `termes-interdits`).
- ADR-055 : « nulle part » précisé (« sur un projet qui a `contraintes.md` »).
- ADR-032 : dit que la portée de `contraintes.md` est portée par la règle ; celle de
  `decisions.md` ne sert que le repli.
- ADR-013 : dit où est le store de run, et qu'un deuxième état global existe.
- Critère : `grep` des cinq tournures ci-dessus ne rend rien ; budget des ADR passe.

**C3 — `**Statut**` devient l'unique source, `adr-audit.md` disparaît (dépend de C1).**
- `memory/adr-audit.md` supprimé ; `grep -rn "adr-audit" backend skills` ne rend rien.
- `test_tracabilite…` lit `decisions.md` : tout ADR « en vigueur » sans portée doit être
  cité dans `contraintes.md`, `## Proposées` comprise.
- ADR-054, 059 et 060 reçoivent `**Portée** : architect` et rejoignent `_CHOIX_PASSES`
  dans `test_adr_pertinents.py`.
- Contrôle de mutation : retirer d'`contraintes.md` une citation d'ADR sans portée fait
  échouer le test.

**C4 — Proposer les règles et ADR manquants (`## Proposées` seulement).**
- Une ADR pour le lien approbation ↔ commit (`approved_sha`, `pushed_sha` ; ticket-492)
  et une pour la protection de la configuration de test (script de `test_command`,
  `conftest.py`, `[tool.pytest*]`…) ; `contraintes.md` les cite en remplacement de
  ADR-039 et ADR-027 pour ces deux règles.
- Proposition qui reprend la règle provider avec ADR-059 : « Seule une indisponibilité
  ou le choix `rapide` déclenche le repli ».
- Proposition qui ajoute ADR-056 à la règle « hors de la racine ».
- Proposition qui reprend la règle ADR-013 avec le store de run.
- Critère : `git diff` de `contraintes.md` ne touche que `## Proposées` ; chaque ADR
  citée existe (`test_tout_adr_cite_existe_encore`) ; chaque ADR nouvelle ≤ 160 mots.

**C5 — À la main : accepter les règles dans `contraintes.md`.**
- La règle « Le verdict reviewer se parse par mot-clé » n'existe plus ; la proposition
  ADR-061 est acceptée.
- Les propositions de C4 sont déplacées dans leur section, l'ancienne règle retirée.
- Critère : `grep "se parse par mot-clé" contraintes.md` ne rend rien ;
  `grep "ADR-059" contraintes.md` rend la règle provider ; la suite de tests passe.

**C6 — À la main : ce que disent les consignes de l'injection.**
- `.claude/skills/write-adr/SKILL.md` : plus de « injected whole », ni de « injectent
  `memory/decisions.md` dans le contexte projet », ni de « trente et un », ni « ADR-001 à ADR-015 (référence) » comme budget courant ; dit
  que `contraintes.md` part par rôle et que `decisions.md` ne part qu'en repli ; dit
  qu'une règle nouvelle passe par `## Proposées` (ADR-055).
- `.claude/skills/code-review/SKILL.md` : la ligne « `memory/decisions.md` part dans
  chaque appel d'agent » remplacée.
- `projects/ide-core/CLAUDE.md` : « Importé lui aussi, donc déjà en contexte » remplacé.
- Critère : `grep -rn "injected whole\|injectent\|trente et un" .claude/skills` ne
  rend rien ; `grep -n "Importé lui aussi" projects/ide-core/CLAUDE.md` non plus.

## Ce que cet audit ne tranche pas

- Le sort d'ADR-013 (compter le store de run comme un état global, ou garder la
  règle telle quelle) : C2 la décrit, un humain choisit si le seuil de cinq change.
- Le sort des historiques (archiver ou garder) : recommandé de garder, mais c'est un
  choix de lecture du journal, pas de comportement.
- L'attribution des numéros d'ADR et de tickets : c'est ticket-659.
