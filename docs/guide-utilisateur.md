# Guide utilisateur — Tessera

Tessera est un IDE qui fait travailler des **agents IA** sur tes projets. Tu décris
ce que tu veux sous forme de **tickets**, et une chaîne d'agents écrit le code, le
teste, l'audite, le relit, le valide et le committe — pendant que tu regardes.

Ce guide s'adresse à quelqu'un qui **utilise** Tessera. Pour comprendre comment il
est construit, va voir [`architecture.md`](architecture.md).

---

## Sommaire

1. [Installer et lancer](#1-installer-et-lancer)
2. [Ajouter un projet](#2-ajouter-un-projet)
3. [Écrire des tickets](#3-écrire-des-tickets)
4. [Lancer un agent sur un ticket](#4-lancer-un-agent-sur-un-ticket)
5. [Lire ce qui se passe](#5-lire-ce-qui-se-passe)
5 bis. [Se repérer dans l'écran](#5-bis-se-repérer-dans-lécran)
6. [Récupérer le travail des agents](#6-récupérer-le-travail-des-agents)
7. [Le mode autonome](#7-le-mode-autonome)
8. [Discuter avec l'agent, pendant qu'il travaille](#8-discuter-avec-lagent-pendant-quil-travaille)
9. [Les agents disponibles](#9-les-agents-disponibles)
10. [Intégration GitHub](#10-intégration-github)
10 bis. [Ce qui reste chez toi, ce qui part dans le dépôt](#10-bis-ce-qui-reste-chez-toi-ce-qui-part-dans-le-dépôt)
11. [Configuration](#11-configuration)
12. [Problèmes fréquents](#12-problèmes-fréquents)

---

## 1. Installer et lancer

### Ce qu'il te faut

Tessera parle à Claude de deux façons — choisis-en une :

| Mode | Quand l'utiliser | Coût |
|------|------------------|------|
| **Abonnement Claude** (défaut) | Usage quotidien sur ta machine | Inclus dans ton abonnement |
| **Clef API Anthropic** | Docker, CI, serveur sans session interactive | Facturé au token |

En mode abonnement (`LLM_PROVIDER=agent_sdk`, la valeur par défaut) **tu n'as pas
besoin de clef API** : il te faut une session Claude Code authentifiée sur la
machine.

### Lancement le plus simple : Docker

```bash
cp .env.example .env
docker compose up --build
```

> En Docker il n'y a pas de session interactive : passe en `LLM_PROVIDER=anthropic_api`
> et renseigne `ANTHROPIC_API_KEY` dans `.env`.

### Lancement local

Prérequis : Python 3.11+ avec [uv](https://docs.astral.sh/uv/), Node.js 24 LTS.

**Linux / macOS**

```bash
make setup    # dépendances + création du .env
make doctor   # vérifie les prérequis
make run      # backend + frontend
```

**Windows** — `make` n'y est pas installé par défaut :

```powershell
.\scripts\tessera.ps1 setup
.\scripts\tessera.ps1 doctor
.\scripts\tessera.ps1 run
```

> `doctor` vérifie Python, `.env`, le workspace, les prompts des agents,
> l'authentification, les symlinks et les ports — et dit quoi corriger.
> Lance-le avant de te demander pourquoi rien ne marche.

Une fois lancé :

- **L'IDE** → <http://localhost:5173>
- **L'API et sa doc interactive** → <http://localhost:8000/docs>

Pour arrêter : `Ctrl+C`.

### Version desktop

```bash
make dev          # terminal 1 — le backend
make tauri-dev    # terminal 2 — la fenêtre native
```

`make tauri-build` produit l'app packagée. Elle lance elle-même le backend
avec `uv`, depuis `TESSERA_BACKEND_DIR`, et lui parle sur l'origine posée dans
`frontend/.env.production` — voir [configuration](configuration.md). Le
backend n'est pas embarqué : `uv` et le dossier `backend/` doivent exister sur
la machine.

---

## 2. Ajouter un projet

Un **projet** est un dossier contenant du code, des tickets et un `CLAUDE.md` qui
explique aux agents le contexte, la stack et les conventions. Tu as quatre façons
d'en obtenir un.

### Créer un projet from scratch

Sidebar → **Nouveau projet**. Tu décris ton idée en langage naturel, l'agent
*project-creator* génère la structure, le `CLAUDE.md` et les premiers tickets.

### Importer un projet existant de ta machine

Sidebar → **Importer un projet**. Deux modes :

- **copy** — Tessera copie le dossier dans son workspace. Ton original n'est jamais
  touché. **C'est le mode recommandé.**
- **symlink** — Tessera crée un lien vers ton dossier. Les agents modifient
  directement tes fichiers. Sous Windows, ce mode exige le **mode développeur** ou
  un lancement en administrateur.

> **Le chemin doit être absolu** : `C:\Users\moi\Desktop\mon-projet`, pas
> `mon-projet`. Si tu colles un chemin depuis l'explorateur Windows
> (« Copier en tant que chemin d'accès »), les guillemets sont retirés
> automatiquement.

> **Non, ton projet n'a pas besoin d'être rangé à côté de l'IDE.** Il peut être
> n'importe où sur ta machine : l'import le copie (ou le lie) vers le dossier
> workspace configuré par `IDE_WORKSPACE_DIR`.

### Cloner un dépôt GitHub

Sidebar → **Cloner un repo**. Colle l'URL, Tessera clone dans le workspace.

### Analyser un projet sans `CLAUDE.md`

Si le projet importé n'a pas de `CLAUDE.md`, lance l'agent *project-analyzer* : il
lit le code et rédige le `CLAUDE.md` à ta place. Relis-le — c'est le document que
**tous** les agents liront avant chaque tâche.

---

## 3. Écrire des tickets

Un ticket est un **fichier Markdown**. Pas de base de données propriétaire : tu peux
les lire, les éditer et les versionner avec git, sans lancer l'IDE.

```
mon-projet/
  tickets/
    todo/          ← en attente
    in-progress/   ← le codeur travaille dessus
    in-review/     ← le reviewer relit
    done/          ← approuvé
    blocked/       ← bloqué (sécurité, ou 3 tours sans approbation)
```

### Anatomie d'un ticket

```markdown
---
id: ticket-007
title: "Ajouter un endpoint de santé"
type: feat          # feat | fix | chore | docs | refactor | test | design
status: todo
priority: high      # critical | high | medium | low
agent: codeur
depends_on: []
created: 2026-09-15
---


#### Tickets légers

Si ton ticket est petit — juste un test supplémentaire, un renommage, une correction — tu peux ajouter `light: true` dans le frontmatter pour le signaler. Par défaut, chaque run approuvé déclenche une passe de documentation : elle coûte plus qu'un petit changement lui-même. Un ticket léger reporte sa documentation au lot suivant ; l'IDE en documentera plusieurs à la fois, une optimisation qui évite de payer une passe entière pour trois lignes de code.

L'audit sécurité et la validation tournent toujours normalement — ce sont des portes critiques qu'on ne saute jamais. Seule la documentation s'allège.



#### Exprimer une dépendance entre tickets

Un ticket peut déclarer une dépendance via le champ `depends_on` : une liste d'identifiants d'autres tickets, comme `depends_on: [ticket-305]` ou `depends_on: [ticket-305, ticket-306]`.

Si un ticket dépend d'un autre, l'IDE t'empêche de le lancer tant que la dépendance n'a pas **complètement mergé** — la branche doit être rebasée, la PR ouverte, la CI validée, et la PR fusionnée dans la branche de base.

Un ticket sans dépendance peut commencer pendant que la PR du précédent attend sa CI : tu gagnes en vitesse en les lançant tous d'un coup. Déclare une dépendance uniquement si ton ticket repose vraiment sur le code d'un autre — par exemple, une API qu'on ajoute et le client qui l'utilise.


## 3 bis. Filtrer et trouver les tickets

Une fois que tu as plusieurs tickets, tu veux souvent en retrouver un particulier. Le tableau mémorise tes filtres (type, priorité, agent, texte) — ils survivent même au redémarrage de l'IDE.

### Quand un filtre cache des tickets

Si tu vois peu de tickets et que le panneau Tickets n'est pas ouvert, il y a souvent un filtre ancien qui s'applique toujours. Le tableau affiche une ligne au-dessus des colonnes dès qu'un filtre est actif :

- Combien de tickets tu vois versus combien il y en a en total (« 4 tickets sur 297 »)
- Le nom de chaque filtre appliqué (type design · priorité high)
- Un bouton **Effacer les filtres** pour tous les enlever d'un coup

Un clic sur ce bouton remet les filtres à zéro — tu verras tous les tickets de nouveau.

# ticket-007 — Ajouter un endpoint de santé

## Objectif

Une phrase : ce que ça doit faire, et pour qui.

## Contexte

Pourquoi c'est nécessaire. Ce qui existe déjà et pourquoi ça ne suffit pas.

## Critères d'acceptation

- [ ] `GET /health` renvoie 200 avec `{"status": "ok"}`
- [ ] Un test couvre le cas nominal
```

### Les critères d'acceptation comptent vraiment

Ce ne sont pas de la décoration : l'agent **validateur** les reprend un par un et
vérifie chacun contre le code produit. Un critère vague (« que ce soit propre »)
donne une validation vague. Un critère vérifiable (« `GET /health` renvoie 200 »)
donne une validation nette.

### Trois façons de créer un ticket

1. **À la main** — crée le fichier `.md` dans `tickets/todo/`.
2. **Depuis l'UI** — Sidebar → **Nouveau ticket**.
3. **Via le planificateur** — Sidebar → **Planifier une évolution**. Tu décris une
   évolution en langage naturel, l'agent découpe en plusieurs tickets cohérents,
   avec leurs dépendances. Tu relis et valides avant écriture.

---

## 4. Lancer un agent sur un ticket

Sélectionne un ticket dans le board, clique sur **Lancer le pipeline**.

Voici ce qui s'enchaîne :

```
1. git checkout -b ticket-007-ajouter-un-endpoint-de-sante
2. Codeur          → écrit réellement les fichiers
3. Testeur         → lance la suite de tests du projet
4. Sécurité        → audit OWASP du diff
5. Reviewer        → relit le diff
6. Validateur      → vérifie les critères d'acceptation un par un
7. Doc-updater     → met à jour README / docs / CLAUDE.md
8. git commit
```

Trois points importants :

- **Le codeur écrit vraiment sur le disque.** Il ne décrit pas le code, il le
  produit.
- **Ce que relisent les agents suivants, c'est le `git diff` réel** — pas le résumé
  du codeur. Ils valident l'implémentation, pas l'intention.
- **Chaque run a sa propre branche git.** Ton travail en cours n'est jamais écrasé.

Les fichiers de verrouillage (`uv.lock`, `package-lock.json`, `pnpm-lock.yaml`,
`yarn.lock`, `poetry.lock`, `Cargo.lock`) apparaissent résumés dans ce diff
pour que le vrai changement reste visible. Le commit, lui, les contient intégralement.

### Si le reviewer n'est pas d'accord

Il renvoie `CHANGES_REQUESTED` avec sa raison, et le codeur repart pour un tour en
tenant compte du retour. Au bout de **3 tours** sans approbation, le ticket passe en
`blocked/` — et le travail produit est **quand même commité** (voir plus bas).

### Si l'audit de sécurité bloque

Une faille `CRITICAL` ou `HIGH` arrête le pipeline immédiatement : le ticket passe
en `blocked/` et le reviewer n'est même pas appelé.

---

## 5. Lire ce qui se passe

Le panneau **Agent Stream** montre le déroulé en direct via WebSocket : quel agent
tourne, ce qu'il écrit token par token, quels outils il utilise, et le verdict de
chaque étape. Quand un agent termine son tour, son entrée s'ajoute au fil — rien
n'est écrasé. Les entrées terminées sont repliées avec leur résumé visible (le
verdict pour le reviewer, la première ligne du compte rendu pour le codeur).
L'entrée en cours, en bas du fil, reste dépliée pour que tu suives en temps réel.

Le panneau **Historique** liste tous les runs passés (persistés en SQLite), avec
leur durée, leur verdict et leur nombre de tours.

Les statuts que tu verras passer :

| Statut | Ce que ça veut dire |
|--------|---------------------|
| `in-progress` | Le codeur travaille |
| `in-review` | Le reviewer relit le diff |
| `done` | Approuvé et commité |
| `blocked` | Sécurité, 3 tours sans accord, ou arbre de travail sale |

---

### Quand les étapes du pipeline s'affichent dans le log

Pendant un run, des étapes du pipeline s'exécutent et émettent des événements affichés dans le log pour que tu saches où tu en es :

- **Audit de sécurité lancé** et **Audit de sécurité terminé** — si bloqué, le verdict s'ajoute à la deuxième ligne
- **Validation lancée** et **Validation terminée** — suivi de l'indication « approuvé » ou pas
- **Documentation lancée** et **Documentation mise à jour** — quand les docs du projet changent
- **Livraison lancée** — affiché juste avant l'ouverture de la PR

Tu les lis dans le même panneau que les agents, dans l'ordre où elles se produisent.



Après l'audit de sécurité, les étapes de **revue** et de **validation** démarrent ensemble — aucune n'attend l'autre. C'est pour gagner du temps : pendant que le reviewer lit le code, le validateur vérifie les critères d'acceptation. Ils peuvent finir à des moments différents, et tu verras l'un puis l'autre revenir avec son verdict.

Pour que le ticket soit approuvé, le reviewer **et** le validateur doivent tous les deux approuver. Si l'un refuse, le ticket est refusé — même si l'autre a approuvé. Tu reçois les motifs de celui qui a refusé, ou des deux si les deux ont refusé.

## 5 bis. Se repérer dans l'écran

Tessera n'essaie pas d'être un éditeur. Monaco est là pour **lire**, pas pour
travailler : il n'a ni LSP, ni debugger, ni recherche multi-fichiers, et il n'en
aura pas. L'édition se fait dans VSCode, qu'on ouvre d'un clic depuis l'en-tête
du projet.

L'écran se lit en quatre colonnes :

| Colonne | Ce qu'on y fait |
|---|---|
| **Le rail** | changer de vue : Projets, Tickets, Fichiers, Historique, Agents, Statistiques |
| **La colonne de projet** | le projet actif, ses actions, et la vue choisie |
| **Le centre** | le tableau des tickets par défaut ; un fichier si tu en ouvres un |
| **La droite** | suivre un run (Agents) ou discuter (Chat) |

**Changer de projet** : le sélecteur en haut de la colonne te permet de passer d'un projet à l'autre. Tu restes sur l'onglet actuellement ouvert — par exemple, si tu consultais les Statistiques du projet A, passer au projet B te garde sur les Statistiques. Seule exception : si tu ouvres un projet depuis l'onglet Projets, tu vas aux Tickets de ce projet.

Les actions d'un projet — ouvrir dans VSCode, lier un dépôt, choisir le mode des
artefacts, retirer le projet — sont dans l'en-tête, qui ne défile jamais.

**Statistiques** donne, sur 7, 30 ou 90 jours : la dépense et les tokens par
jour, la part de chaque agent, modèle et projet, le taux d'approbation des runs,
leurs durées et les derniers runs. La comptabilité inclut **tous** les appels du pipeline — codeur, reviewer, sécurité, validateur, documentation — pas uniquement le codeur. Sans projet sélectionné, la vue couvre tous
les projets. Les jours sont des jours UTC. La colonne de gauche garde la dépense
par ticket. C'est le panneau à regarder après tes premiers runs : il donne
l'échelle réelle, qui est rarement celle qu'on imagine.

---


### Fermer un run achevé

Une fois qu'un run est entièrement complété — sa revue approuvée et sa livraison effectuée (le cas échéant) — tu vois un bouton « Fermer » dans le résumé. Un clic le retire du panneau de Supervision pour dégager l'écran et passer aux tickets en cours ou suivants.


#### Signes de fin du run

Quand le pipeline finit (approuvé ou bloqué), la carte du run change d'aspect :

- **Le chrono s'arrête.** Il affiche l'heure exacte de fin et ne compte plus les secondes.
- **Le résumé en haut se met à jour :**
  - `PR #42 mergée` si livraison réussie (le numéro est un lien vers GitHub)
  - `Livraison : <raison>` si elle n'a pas abouti (dépôt absent, CI rouge, branche divergée…)
- **Le bouton « Fermer »** est maintenant actif pour masquer la carte.

Par défaut, une fois approuvé, le pipeline enchaîne jusqu'à la livraison — tant qu'il y a un dépôt git et que le projet l'autorise. Sinon, tu vois pourquoi ça s'est arrêté.


### Rouvrir un run terminé

Un run une fois terminé disparaît de la Supervision après un rechargement ou une fermeture de session. Mais tu peux le relire à tout moment depuis l'historique :

- Ouvre le panneau **Historique** (panneau de droite) — il liste les runs récents avec leur verdict et leur date
- Clique sur une ligne pour rouvrir la vue complète du run : étapes, cartes par agent (codeur, testeur, sécurité, reviewer, validateur), verdict final
- La vue rouverte est **en lecture seule** : pas de bouton pour arrêter le run, pas de champ pour envoyer un message à l'agent, pas de chrono qui avance
- Un bouton **Fermer** te ramène à l'historique

C'est utile pour vérifier les détails d'un run après coup — comment chaque étape s'est déroulée, pourquoi un ticket a terminé bloqué — sans relancer la machine.



La carte du run affiche maintenant l'**état de la PR** en temps réel, même après fermeture. Si tu as fermé le run pendant que la PR attendait la CI, tu reverras « PR #42 — en attente de CI » la prochaine fois. Une heure plus tard, en rouvrant le run, tu verras « PR #42 mergée ». Si la CI a rejeté la PR, l'IDE affiche le motif de blocage.

Tu peux donc suivre la livraison d'un ticket **après** le run, sans relancer le pipeline ni vérifier GitHub : ouvre juste la carte fermée.

### La frise d'étapes

En haut du panneau des agents s'affiche une barre avec les étapes que ce projet utilise : une pastille arrondie par étape, avec une couleur qui te dit où elle en est.

Les couleurs :
- **Bleu** : cette étape tourne en ce moment
- **Vert** : elle est finie, tout a été accepté
- **Rouge** : elle a refusé quelque chose (audit bloque, validation n'approuve pas)
- **Gris** : elle n'a pas encore commencé

Les étapes du pipeline sont **sécurité**, **revue**, **validation**, **documentation** et **livraison**. Si le projet n'en active pas une (par exemple pas d'audit de sécurité), sa pastille ne s'affiche pas.

La pastille en bleu te dit en un coup d'œil où tu en es, sans lire le log ni quitter l'IDE.



Quand revue et validation tournent ensemble, tu vois deux pastilles bleues actives au même moment : la pastille revue et la pastille validation. Chacune devient verte quand elle approuve, ou rouge si elle refuse. Elles ne finissent pas forcément au même moment : l'une peut passer au vert avant l'autre.

### Le fil du run : tous les verdicts en un seul endroit

Quand tu observes un run qui a tourné plusieurs fois, tu vois maintenant un seul fil chronologique complet. Ce fil affiche tous les passages — codeur, reviewer, et maintenant aussi **sécurité** et **validateur**. C'est ce fil qui t'explique pourquoi le codeur repart tourner.

**Exemple** : le reviewer approuve au tour 1, mais le validateur refuse car un critère d'acceptation n'est pas satisfait. Le fil du run affiche :

1. Codeur — Tour 1
2. Reviewer — Tour 1 — ✓ APPROVED
3. **Sécurité — Tour 1** — ✓ Audit passé
4. **Validateur — Tour 1 — ✗ Changements demandés**
5. Codeur — Tour 2 (repart pour corriger)

Ce que tu vois dans le fil pour chaque verdict :
- **Sécurité** : son verdict (approuvé ou bloquant) et un résumé de ses findings
- **Validateur** : son verdict (approuvé ou changements demandés), puis en détail, pour chaque critère d'acceptation du ticket, son état (✓ réussi / ✗ échoué) et la note du validateur

Ce fil est le même partout — que tu regardes dans la **Supervision** (onglet Agents) ou dans l'**onglet du run**, tu vois l'histoire complète. Plus besoin de chercher dans les logs : tu sais d'un coup d'œil pourquoi le codeur repart.


#### Verdicts lisibles dans le log

Le Pipeline log énumère maintenant chaque étape du pipeline avec son résultat exact :

- **Tests** : « Tests : verts » ou « Tests : rouges — retour au codeur » si le testeur a tourné. Un échec renvoie au codeur sans passer à la revue.
- **Validation** : « Validation : approuvée » ou « Validation : refusée ». C'est le verdict du validateur tel qu'il l'a décidé.
- **Livraison** : « PR #42 », « PR #42 mergée » ou la raison de l'arrêt (CI non verte, branche divergée, absence de dépôt…).

Le log reste affiché une fois le run clos, pour relire ce qui s'est passé.



Quand revue et validation sont parallèles, leurs événements s'entrelaçent dans le fil : le reviewer démarre, puis le validateur démarre, puis des tokens du reviewer, puis des tokens du validateur, etc. Si les deux refusent, tu vois les deux motifs avec le nom de chaque étape.

## 5 ter. Après le run : fusion automatique

Quand le run se termine approuvé, l'IDE :
- Rebase ta branche sur la branche de base
- Ouvre une pull request sur GitHub
- Finit le run — tu vois le badge ✅

Ensuite, la pull request se fusionne seule en arrière-plan :
- Elle attend les checks CI (tests, qualité de code…)
- Dès que tout est vert, elle se fusionne automatiquement
- Le commit arrive sur la branche de base

Tu peux suivre son état en cliquant sur le numéro de PR du ticket ou en consultant l'historique. Aucune action n'est attendue de ta part — tout est automatique.

En mode autonome, le ticket suivant commence immédiatement (le projet n'est plus verrouillé). S'il dépend du précédent (`depends_on`), la file attend la fusion du parent.

Si une étape échoue — conflit de rebase, ou vérification CI — tu vois l'erreur dans le run. La PR n'est ouverte que si la livraison a réussi.

Si la CI échoue, le ticket passe en `blocked` — tu dois corriger le problème et relancer le pipeline. Il n'y a pas de relance automatique.

En mode file (`queue`), un seul merge par projet peut être en cours à la fois. Les tickets suivants attendent que le précédent soit fusionné avant de pouvoir commencer leur propre livraison.

## 6. Récupérer le travail des agents

**À chaque run, quel que soit le verdict, le travail est commité** sur la branche du
ticket. Rien n'est jamais perdu, et l'arbre de travail reste propre pour le ticket
suivant.

Deux messages de commit possibles :

| Verdict | Message |
|---------|---------|
| Approuvé | `feat: ticket-007 — Ajouter un endpoint de santé` (le type vient du ticket) |
| Non approuvé | `chore: ticket-007 — unapproved work (security block: ...)` |

Pour inspecter ce qu'un agent a produit :

```bash
cd <ton-projet>
git log --oneline --all           # voir toutes les branches de tickets
git show ticket-007-ajouter-un-endpoint-de-sante
git diff main..ticket-007-ajouter-un-endpoint-de-sante
```

Pour récupérer un travail approuvé :

```bash
git merge ticket-007-ajouter-un-endpoint-de-sante
```

> **La comptabilité de Tessera fait l'objet d'un commit séparé.** Les changements de
> statut de tickets et le journal de pipeline arrivent dans un commit
> `chore: Tessera pipeline bookkeeping`, jamais mélangés au travail du codeur.

---

## 7. Le mode autonome

`POST /api/v1/orchestrator/run-autonomous` enchaîne les tickets `todo/` tout seul,
par ordre de priorité, en respectant les dépendances.

Ce qu'il faut savoir avant de le lancer :

- **Chaque ticket approuvé devient la base du suivant.** Un plan de tickets
  séquentiels s'empile donc correctement.
- **Un ticket rejeté ne contamine pas le suivant.** Son travail reste sur sa branche,
  et le ticket d'après repart de la dernière base approuvée.
- **Un ticket bloqué ne gèle pas la file.** Il passe en `blocked` et l'orchestrateur
  passe au suivant.

Le run s'arrête aussi de lui-même s'il atteint `RUN_MAX_BUDGET_USD` (5 $ par
défaut) : le plafond est vérifié **entre** deux tickets, jamais au milieu d'un,
pour qu'aucun travail ne reste non commité.

Commence par des lots courts (`max_tickets: 3`) le temps de calibrer la qualité de
tes tickets.

---


**Depuis la Vue Tableau**

Tu n'as pas besoin de passer par la sidebar pour composer et lancer la file — la Vue Tableau t'offre exactement les mêmes contrôles. Chaque carte affiche un bouton « Ajouter à la file » ou « Retirer de la file ». Quand tu as sélectionné au moins un ticket, une barre apparaît au-dessus des colonnes : elle montre le nombre de tickets en attente et propose « Lancer la file » et « Vider ». Un ticket ajouté d'un côté se voit aussitôt de l'autre — sidebar et Vue Tableau restent synchronisées.

## 8. Discuter avec l'agent, pendant qu'il travaille

Le panneau de droite a deux onglets : **Agents**, qui observe un run de
pipeline, et **Chat**, où tu discutes librement du projet.

### Pendant un run : l'agent demande, tu interviens

Sous l'onglet **Agents**, tant qu'un run tourne, deux champs distincts
apparaissent — et la distinction compte.

**La question de l'agent.** Un agent qui bute sur une ambiguïté que ni le
ticket, ni le code, ni les ADR ne lèvent peut suspendre son tour et te
demander. La question s'affiche en attente ; ta réponse relance le run là où il
s'était arrêté.

Il ne t'attendra pas indéfiniment. Passé quelques minutes, il **reprend seul en
énonçant l'hypothèse qu'il retient**, et cette hypothèse part dans le rapport du
run — donc elle est relisible. C'est délibéré : un run suspendu tient du travail
non commité, et bloquerait tous les tickets qui suivent. En mode autonome, où
personne ne regarde, la question ne t'attend même pas.

**La consigne pour le prochain tour.** Elle n'attend rien et sera lue par le
prochain agent à parler, quel qu'il soit. « Pense aux tests », « utilise
pathlib » : ça infléchit la suite sans interrompre ce qui est en cours.

Les deux ne se confondent jamais. Une consigne envoyée pendant qu'une question
est posée ne vaut pas réponse à cette question — sinon un « au fait, pense aux
tests » deviendrait la réponse à « on casse l'API ? ».

#### Trouver où répondre : les runs en attente d'abord

Lorsque plusieurs agents tournent en parallèle, ceux qui t'attendent — qui ont posé une question — sont affichés en premier dans la Supervision. Sur chaque carte « attend une réponse », un bouton « Répondre » te sélectionne le run et te place directement dans le champ de réponse. Tu n'as pas à chercher.

Si tu choisis une autre carte explicitement pour la lire, ta sélection y reste stable — elle ne bascule pas si un autre run demande quelque chose pendant ce temps.

### Le chat, hors pipeline

Le chat n'est pas un pipeline. Il sert à décider **quoi** ticketiser, à
comprendre un bout de code, à faire une modification ponctuelle — sans passer
par le cycle complet codeur → reviewer → validateur.

Les conversations du chat sont maintenant listées par projet, triées de la plus
récente à la plus ancienne. Chacune a un titre (extrait du premier message,
coupé à 60 caractères) et une date. Elles persistent : tu peux reprendre une
ancienne conversation sans recommencer à zéro.

### Ce que l'agent peut faire

- Lire n'importe quel fichier du projet, chercher dedans
- Écrire et modifier des fichiers, y compris créer des tickets
- Lire le `CLAUDE.md`, les tickets ouverts et les ADR du projet

### Ce qu'il ne peut pas faire

- **Exécuter des commandes** — aucun outil shell ne lui est donné
- Lancer un pipeline lui-même : il peut le suggérer, tu décides

### Ses écritures sont commitées, pas laissées en vrac

Quand l'agent modifie des fichiers, son travail est **commité automatiquement**
sur une branche `chat-<horodatage>`, jamais sur ta branche courante. Deux
raisons :

1. Tu peux inspecter, récupérer ou jeter son travail sans rien risquer :
   `git show chat-20260915-143000`
2. L'arbre de travail reste propre. Sinon, le prochain ticket que tu lances
   partirait en `blocked` sans qu'aucun agent n'ait tourné.

Un échange purement conversationnel ne crée ni branche ni commit.

### Le coût est affiché

En haut du panneau : `0.250 / 2.00 $`. C'est le cumul de **cette
conversation**, et son plafond. Atteint, la conversation refuse de continuer —
ouvre-en une nouvelle, ou relève `CHAT_MAX_CONVERSATION_USD`.

> Le garde-fou `LLM_MAX_BUDGET_USD` borne **un appel**. Sans ce second plafond,
> une longue discussion épuiserait ton quota sans que rien ne le montre.

La conversation survit à un rechargement de la page.

---

## 9. Les agents disponibles

| Agent | Rôle |
|-------|------|
| `codeur` | Implémente le ticket, écrit les fichiers |
| `reviewer` | Relit le diff, approuve ou demande des changements |
| `testeur` | Lance la suite de tests du projet (pytest / npm / cargo) |
| `securite` | Audit OWASP du diff — bloque sur CRITICAL/HIGH |
| `validateur` | Vérifie les critères d'acceptation un par un |
| `doc-technique` | Met à jour la documentation technique par lot, en fin de file, par modifications ciblées (ADR-035) |
| `doc-fonctionnelle` | Idem pour le guide utilisateur, sans noms de classes |
| `chat` | Discute du projet, lit et écrit ses fichiers (onglet Chat) |
| `planificateur` | Découpe une évolution décrite en langage naturel en tickets |
| `architect` | Intervient sur les tickets de type `design` |
| `project-creator` | Crée un projet de zéro par conversation |
| `project-analyzer` | Génère un `CLAUDE.md` en lisant un code existant |
| `agent-creator` | Crée un nouvel agent sur mesure, par conversation |

Chaque agent est un **prompt Markdown** dans `agents/prompts/`. Tu peux les lire, les
modifier, et en ajouter — via **Sidebar → ⚙ Agents**, ou en déposant un fichier.

### Activer ou désactiver des étapes

Toutes les étapes ne sont pas obligatoires. La configuration du pipeline de chaque
projet permet de désactiver le testeur, la sécurité ou le validateur, et de
régler `max_review_rounds`. La documentation ne se règle pas par ticket : elle
se met à jour à la fin d'une file ou d'un run autonome (ADR-035).

### Rôles de jugement sur Ollama

Les rôles `validateur`, `doc-technique`, `doc-fonctionnelle`,
`project-analyzer` et `agent-creator` ne font qu'un appel texte → JSON. Tu
peux les configurer pour tourner sur [Ollama](https://ollama.com) à coût nul.

Garde `securite` sur Claude : rejoué sur une traversée de chemin réelle,
`qwen3-coder:30b` a rendu `PASS` trois fois sur trois.

Pour chaque projet :
1. Lance un serveur Ollama : `ollama pull qwen3-coder:30b` (~19 Go)
2. Définis `OLLAMA_BASE_URL` dans `.env` (défaut : `http://127.0.0.1:11434`)
3. Configure le rôle dans `agents.json` du projet : `"provider": "ollama"`,
   et déclare son repli : `"fallback": {"provider": "agent_sdk", "model": "claude-haiku-4-5"}`

Si le serveur n'est pas disponible, un rôle qui déclare un repli bascule sur
Claude, ce qui est visible dans l'historique des appels (tableau des coûts). Sans
repli déclaré, l'étape échoue — et la sécurité comme le validateur refusent
alors le run (ADR-039, ADR-046). Le codeur, le
reviewer et le chat restent toujours sur Claude — ils ont besoin des outils fichier
que seul le SDK fournit.

---

### Direction visuelle pour les interfaces

Quand un ticket crée ou modifie une interface — une route qui ajoute des écrans, un composant UI — le codeur commence par établir une charte visuelle avant d'écrire du code.

Il crée cette charte dans `memory/design.md` s'il n'y en a pas une :

- Une direction en une phrase, avec une référence (« sobre et épurée, comme le design de GitHub »)
- Cinq familles de couleurs maximum, chacune avec un rôle
- Une échelle typographique
- Une échelle d'espacement et des rayons

Tu dois revoir et approuver cette charte avant qu'il ne touche au code.

Puis le codeur code l'interface en respectant ces règles :

- **Aucune valeur en dur** (couleur, taille, espacement) — tout vient des tokens de la charte
- **Une seule action principale par vue**
- **États vide, chargement et erreur** prévus
- **Contraste AA**
- **Une vue de travail montre des données**, pas des marges
- **Pas de dégradé décoratif**, pas de cartes ombrées partout, pas d'emoji en guise d'icônes

Cette charte garantit une cohérence dans le temps : chaque ticket UI la respecte, tu ne risques plus de passer d'une couleur à l'autre ou d'une taille arbitraire.

**Sur les projets existants**, cette direction n'est pas active par défaut. Tu peux l'ajouter en éditant `agents.json` : ajoute `"tessera:design-ui"` dans la clé `skills` du codeur et de l'architect.


### Ce que le testeur attrape

Le testeur lance les mêmes outils que ta CI : `pytest` et `mypy` pour Python, `tsc` pour TypeScript, puis `eslint` et `vitest` pour le frontend. Un ticket n'échouera plus soudain en CI sur une erreur de typage ou de lint — le pipeline les détecte tous maintenant, avant même que la PR soit ouverte.

## 10. Intégration GitHub

Renseigne `GITHUB_TOKEN` et `GITHUB_REPO` dans `.env` pour débloquer :

- **Import d'issues** → chaque issue devient un ticket
- **Synchronisation bidirectionnelle** tickets ↔ issues
- **Création de PR** depuis un ticket terminé — le titre respecte le format Conventional Commits, avec le type du ticket (par exemple `feat: ticket-007 — Ajouter un endpoint de santé`)
- **Statut CI** de la PR remonté dans l'UI

Une PR approuvée peut être mergée automatiquement une fois que la CI passe au vert, selon la configuration du projet. La livraison attend jusqu'à 2 minutes que les checks CI soient enregistrés par GitHub — l'absence momentanée de checks n'est pas interprétée comme un verdict favorable.

---

## 10 bis. Ce qui reste chez toi, ce qui part dans le dépôt

Tessera ajoute quatre choses à un projet : `tickets/`, `memory/`, `CLAUDE.md`
et `agents.json`. Elles n'ont pas leur place dans tous les dépôts.

Chaque projet déclare son mode, dans le panneau **Git & artefacts** :

- **local** — les artefacts restent sur ta machine. L'exclusion est écrite dans
  `.git/info/exclude`, jamais dans `.gitignore` : ce dernier est lui-même
  versionné, donc le modifier annoncerait dans un diff exactement ce qu'on
  voulait garder hors du dépôt.
- **versionné** — ils partent avec le projet. C'est ce qu'on veut d'un projet
  personnel : les décisions sont tracées et survivent à la machine.

**Le défaut protège** : seul un projet *créé* par l'IDE est versionné. Un projet
importé ou cloné existait avant Tessera — souvent chez quelqu'un d'autre — et
reste local. On peut toujours choisir de partager ensuite ; on ne peut pas
défaire un push.

Une limite à connaître : `.git/info/exclude` n'agit que sur les fichiers **non
suivis**. Si un dépôt versionne déjà un `CLAUDE.md`, tes modifications
continueront d'y partir. L'IDE te le signale.

Le code produit par les agents, lui, n'est jamais exclu : c'est ce que tu livres.

---

### Cadrages et artefacts locaux

Ton cadrage (ticket `design`) crée de nouvelles décisions dans `memory/decisions.md` ou des tickets dans `tickets/todo/`. Si ton projet garde ces artefacts locaux (non versionnés), ces fichiers ne sont jamais commitées — ils restent chez toi. Cependant, le reviewer et le validateur les voient quand même, car le diff relu inclut un résumé textuel des changements. Ton cadrage peut donc être approuvé et mis en œuvre même s'il ne crée ni ne modifie aucun fichier du code.


### Configuration locale : jamais committée

`agents.json`, `.claude/settings.json` et `.github/workflows/` ne voyagent **jamais** dans un commit du pipeline, même si tu les modifies pendant un run.

Si tu changes un modèle d'agent via l'écran Agents de l'IDE pendant qu'un ticket est en cours, par exemple, cette modification reste dans ton arbre de travail mais n'est pas committée. Le run te le signale dans son rapport. Cela garantit que la configuration de l'IDE ne voyage pas accidentellement avec le travail d'un ticket.

## 11. Configuration

Tout est dans `.env` (copié depuis `.env.example`) :

| Variable | Défaut | À quoi ça sert |
|----------|--------|----------------|
| `LLM_PROVIDER` | `agent_sdk` | `agent_sdk` (abonnement) ou `anthropic_api` (crédits) |
| `ANTHROPIC_API_KEY` | — | Requis **uniquement** en mode `anthropic_api` |
| `LLM_MAX_TURNS` | `30` | Plafond d'allers-retours outil pour un agent |
| `LLM_MAX_BUDGET_USD` | `1.0` | Plafond de dépense d'un **seul** appel agent |
| `RUN_MAX_BUDGET_USD` | `5.0` | Plafond cumulé d'un **run autonome** (`0` = aucun) |
| `CHAT_MAX_CONVERSATION_USD` | `2.0` | Plafond de dépense d'une **conversation** du chat |
| `IDE_WORKSPACE_DIR` | `~/tessera-workspace` | Où vivent tes projets |
| `IDE_PROMPTS_DIR` | `agents/prompts/` | Où vivent les prompts des agents |
| `IDE_LOG_LEVEL` | `INFO` | Verbosité des logs |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Serveur Ollama (pour les rôles de jugement, voir section 9) |
| `GITHUB_TOKEN` | — | Token GitHub |
| `GITHUB_REPO` | — | Dépôt cible, format `owner/repo` |
| `STATIC_TOKEN` | — | Si défini, l'API exige `Authorization: Bearer <token>` — WebSockets comprises, via `?token=`. Côté UI : `VITE_STATIC_TOKEN` dans `frontend/.env.local` |

`LLM_MAX_TURNS` et `LLM_MAX_BUDGET_USD` sont tes garde-fous contre un agent qui part
en boucle. Ne les augmente qu'en connaissance de cause.

> **Si tu exposes Tessera sur un réseau**, définis `STATIC_TOKEN`. Sans lui l'API
> est ouverte — c'est acceptable en local, pas ailleurs.

---

## 12. Problèmes fréquents

### « Le dossier source n'existe pas : ...\backend\"C:\..." »

Ton chemin est relatif ou entouré de guillemets. Donne un chemin **absolu**. Les
guillemets sont désormais retirés automatiquement.

### « Impossible de créer le lien symbolique » (Windows)

Les symlinks demandent le **mode développeur** Windows ou un lancement en
administrateur. Le plus simple : réimporte en mode **copy**.

### Un ticket passe en `blocked` sans qu'aucun agent n'ait tourné

L'arbre de travail du projet était sale au démarrage. C'est un filet de sécurité :
quelque chose a modifié des fichiers **suivis** en dehors de Tessera. Committe ou
annule ces changements, puis repasse le ticket en `todo`.

### Le pipeline tourne mais rien ne change dans les fichiers

Vérifie `LLM_PROVIDER`. Seul le mode `agent_sdk` donne les outils fichier au codeur.

### Des `500` inexplicables, et un port 8000 impossible à libérer

C'est le **worker `uvicorn --reload` orphelin**. Tuer le processus parent laisse
son enfant vivant : il garde le port et continue de servir le code tel qu'il
était à son dernier rechargement. Le symptôme distinctif : le port est tenu par
un PID que `Get-Process` ne trouve pas.

```powershell
.\scripts\tessera.ps1 stop              # le cible par sa ligne de commande
taskkill /F /PID <pid>  # en dernier recours
```

Ne lance pas `--reload` si tu enchaînes des modifications de fichiers.

### Les agents ignorent mes conventions

Ils lisent le `CLAUDE.md` **du projet**. S'il est vide, générique, ou périmé, ils
travaillent à l'aveugle. C'est le fichier le plus rentable à soigner.

### Le reviewer refuse systématiquement

Tes critères d'acceptation sont probablement trop vagues, ou le ticket demande trop
de choses à la fois. Un ticket = un changement cohérent.

### Les tests échouent alors qu'ils passent chez moi

Le testeur lance la commande configurée dans le pipeline du projet, depuis la racine
du projet, avec un timeout de 120 s.

---

## Pour aller plus loin

- [`architecture.md`](architecture.md) — comment Tessera est construit
- [`ticket-strategy.md`](ticket-strategy.md) — comment découper un backlog
- `projects/ide-core/memory/decisions.md` — les ADR, dont **ADR-017** (couche LLM) et
  **ADR-018** (isolation git du pipeline)
