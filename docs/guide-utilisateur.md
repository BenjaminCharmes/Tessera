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
- **L'API et sa doc interactive** → <http://localhost:8100/docs>

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

### Créer un projet depuis le gabarit FastAPI + React

La fenêtre **Nouveau projet** propose deux types :

**Projet vide** : l'IDE crée la structure Tessera (tickets, mémoire,
`CLAUDE.md`, `agents.json`) et initialise le dépôt git ; le code reste à
écrire.

**Gabarit FastAPI + React** : l'IDE génère une base prête à développer.
- Backend `backend/` (FastAPI, pytest, mypy) et frontend `frontend/` (React,
  Vite, TypeScript, Tailwind), tous les marqueurs remplacés.
- Deux ports libres attribués et affichés après création (backend à partir de
  8020, frontend à partir de 5190), jamais déjà pris par un autre projet.
- Un `agents.json` complet : les rôles du pipeline, `autonomy: merge`,
  `merge_without_ci: true`, une `test_command` qui lance toute la suite.
- Un dépôt git local initialisé.

Il te reste deux choses à faire toi-même :
1. Écrire le `CLAUDE.md` du projet (ce qu'il fait, ses contraintes).
2. Créer le dépôt GitHub et le lier (voir « Intégration GitHub ») : l'IDE ne
   le crée jamais sans toi.

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


## 2 bis. Naviguer entre les projets

La barre latérale te permet de voir rapidement tes projets, rangés par catégorie. Quand tu as beaucoup de projets, tu peux les explorer autrement : en cliquant sur l'onglet **Projets** en haut de la zone centrale, tu obtiens une vue en cartes.

### Afficher la liste des projets

Tu vois trois onglets en haut de la zone centrale : **Kanban**, **Projets** et éventuellement **Chat**. Clique sur **Projets** pour voir la grille de cartes.

### Chercher un projet

Un champ de recherche te permet de taper le nom d'un projet, son identifiant ou sa description — sans tenir compte de la casse ni des accents. Par exemple, taper « deminéür » filtre sur le projet `demineur`.

### Filtrer par catégorie

Des pastilles colorées au-dessous du champ affichent tes catégories. Clique sur une pastille pour garder seulement ses projets ; clique sur « Toutes » pour revenir à la liste complète. Chaque pastille affiche le nombre de projets de sa catégorie.


Tu organises tes projets par catégorie (par exemple : frontend, backend, infrastructure). Chaque catégorie peut être **repliée** pour gagner de la place.

**Replier et déplier**

Clique sur le titre de la catégorie (à côté du chevron) pour la replier. Le chevron tourne, et tu vois apparaître un **badge** affichant le nombre de projets cachés. Passe la souris dessus : une info-bulle te donne la liste complète — « 3 projets : demineur, serpent, cookie-clicker ».

Clique à nouveau sur le titre pour redéplier.

**L'état est sauvegardé**

Le navigateur retient les catégories que tu as repliées. Quand tu reviens plus tard, tu les retrouves dans le même état — à la fois dans la barre latérale et dans la vue « Projets ».

**Pendant une recherche**

Si tu cherches un projet dans la vue « Projets » et qu'il y a des résultats dans une catégorie repliée, cette catégorie se **déplie automatiquement** pour te montrer les résultats. Quand tu effaces la recherche, elle revient à son état replié précédent.

**Le projet actif reste visible**

Le projet sur lequel tu travailles, ou celui qu'un agent exécute en ce moment, est toujours affiché — même si sa catégorie est repliée. L'IDE ne la replie jamais d'elle-même ; c'est toi qui dois la replier manuellement si tu veux.

### Trier les projets

Un menu te propose plusieurs ordres :
- **Nom** : alphabétique
- **Activité récente** : les projets modifiés en dernier d'abord
- **Création récente** : les plus jeunes d'abord

### Lire une carte de projet

Chaque carte affiche :
- L'**icône** du projet (ou l'initiale si pas d'icône)
- Le **nom**, l'**identifiant** et la **catégorie**
- La **description**, limitée à 3 lignes
- Le **lien du dépôt** : clique dessus pour l'ouvrir dans un nouvel onglet, sans quitter l'IDE
- Les **dates** : création et dernière activité, en relatif (« il y a 2 j ») avec la date exacte en info-bulle
- Les **compteurs** : nombre de tickets à faire, en cours, bloqués et faits
- Un **point animé** si un run tourne sur ce projet

Le projet actuellement actif est marqué d'une barre violette sur la gauche.

Chaque carte affiche aussi deux badges sur les services du projet :

- Un badge te dit si le projet a une application à lancer.
- Un badge te dit si cette application tourne actuellement sur ta machine.

Cela te permet de voir rapidement quel projet peut être lancé et lequel tourne déjà, sans ouvrir sa fiche.

### Contrôler les services depuis la vue Projets

Si un projet déclare un service, sa carte affiche un bouton « Lancer » dans sa rangée basse. Clique-le pour démarrer l'app du projet **sans quitter la vue Projets** — pas besoin d'ouvrir les tickets pour changer l'état d'un service.

- Le bouton devient « Arrêter » si le service est actif
- Pendant l'appel, le bouton est grisé
- Un échec affiche un message court en rouge sous le bouton ; le bouton reste cliquable pour réessayer

La vue Projets affiche en temps réel un inventaire de toutes les apps qui tournent sur ta machine. Chaque app affiche :

- Son nom et le projet auquel elle appartient
- Son identifiant de processus (PID)
- Les ports qu'elle écoute
- Sa consommation mémoire (incluant tous ses processus enfants)
- Son origine : **Tessera** (lancée par l'IDE) ou **externe** (lancée en dehors de l'IDE)

Le backend Tessera lui-même (port 8100) et son interface web (port 5173) sont exclus de cet inventaire.

Pour arrêter une app, clique sur **Arrêter** à côté. L'IDE ferme le processus et tous ses descendants. Si elle a été lancée par Tessera, elle ne relancera pas automatiquement.

Une app **externe** est une application que tu as démarrée en dehors de l'IDE — par exemple une API, un serveur, ou une interface web — qui écoute un port connu d'un projet. L'IDE la détecte automatiquement et te permet de l'arrêter directement depuis la vue Projets. C'est utile quand tu as oublié une app en train de tourner — tu vois sa consommation mémoire et tu peux la fermer en un clic.

### Capturer les écrans d'un projet

Pour comparer une app à sa maquette (`design/maquette/`), Tessera prend en un geste quatre captures de chaque écran : téléphone (390 px) et ordinateur (1440 px), thème clair et thème sombre.

Déclare d'abord les écrans dans l'`agents.json` du projet, dans une section `captures` :

```json
"captures": {
  "url": "http://localhost:5196",
  "ecrans": [
    { "nom": "accueil", "chemin": "/" },
    { "nom": "quiz", "chemin": "/#jouer", "clic": "Jouer" }
  ]
}
```

- `url` : l'adresse où l'app du projet répond (`http://` ou `https://`).
- `ecrans` : la liste des écrans. `nom` sert de nom de fichier (lettres minuscules, chiffres et tirets ; le reste est remplacé par un tiret) et `chemin` commence par `/`.
- `clic` (facultatif) : le texte exact d'un bouton ou d'un onglet à cliquer avant la capture, pour atteindre un écran qui n'a pas d'adresse propre.

Lance ensuite l'app du projet, puis demande les captures avec `POST /api/v1/projects/{id}/captures`. La réponse liste les images, nommées `<nom>-<largeur>-<thème>.png` — par exemple `accueil-390-sombre.png`. Chacune se récupère avec `GET /api/v1/projects/{id}/captures/{fichier}`.

Les images sont rangées dans le dossier d'état de l'IDE, sous `captures/<projet>/`, **hors du dépôt du projet** : elles ne finissent dans aucun commit. Chaque demande remplace celles du tour précédent.

#### Une app qui exige un jeton

Si l'app affiche « Jeton d'accès requis » tant qu'on n'a pas ouvert de session, ajoute une clé `session` à la section `captures` :

```json
"session": { "chemin": "/api/session", "jeton_env": "ACCESS_TOKEN", "fichier_env": "backend/.env" }
```

- `chemin` : la route qui échange le jeton contre un cookie de session. Elle reçoit un `POST` avec le corps `{"token": "<jeton>"}`. Commence par `/`.
- `jeton_env` : le nom de la variable qui porte le jeton.
- `fichier_env` (facultatif, `.env` par défaut) : le fichier qui la contient, relatif à la racine du projet. Un chemin qui en sort est refusé.

Tessera lit le jeton **côté serveur**, dans ce fichier, et le transmet au script par son entrée standard : il n'apparaît ni dans `agents.json`, ni dans la réponse de `POST …/captures`, ni dans les journaux, ni dans la ligne de commande du processus. Le script ouvre la session dans le navigateur, puis prend les captures. Sans clé `session`, rien ne change.

Une clé `session` présente mais incomplète rend toute la section `captures` inutilisable (409 « ne déclare aucune capture ») : mieux vaut un refus que des captures de l'écran de connexion.

Tessera répond **409** dans ces cas :

- le projet ne déclare pas de section `captures` (ou elle ne contient aucun écran valide) ;
- la `session` est déclarée mais la variable est absente ou vide dans le fichier indiqué — la capture n'est alors pas lancée ;
- l'app ne répond pas à l'`url` déclarée — lance-la d'abord.

Si le navigateur échoue en cours de route, la réponse est **502** et porte le message du script. La prise de vue utilise le Playwright du frontend de Tessera : `node` doit être dans le PATH, et le navigateur installé (`npx playwright install chromium` dans `frontend/`).

Tessera ne compare pas les captures à la maquette : tu les regardes côte à côte.

### Lancer une file depuis la carte d'un projet

Tu vois un bouton **« File (N) »** sur une carte si le projet a au moins un ticket « à faire ». Clique dessus pour envoyer tous les tickets du projet dans le pipeline.

Une confirmation s'affiche sur la carte : « Lancer N tickets ? » Clique **« Lancer »** pour poursuivre.

- Les tickets lancés sont ceux au statut « à faire », dans l'ordre de leur id.
- Quand tu cliques, l'IDE reste dans la vue d'ensemble — tu n'entres pas dans le projet.
- Si un run tourne déjà sur ce projet, le bouton est grisé et tu vois l'infobulle « Un run est en cours ».
- Si le lancement échoue (par exemple, un autre run a démarré pendant que tu confirmais), un message d'erreur court s'affiche en rouge.

### Sélectionner un projet

Clique sur une carte pour la sélectionner. La zone centrale passe au Kanban de ce projet, comme si tu l'avais choisi dans la barre latérale.

Quand tu cliques sur une carte de projet, le projet est sélectionné (barre violette, colonne de gauche à jour) et tu restes sur la vue Projets — tu n'es pas renvoyé à la liste des tickets. Changer de projet n'interrompt pas ta tâche de lecture ou de navigation.

L'onglet que tu consultais avant le changement se maintient : si tu regardais un tableau Kanban, tu vois le tableau du nouveau projet ; si tu consultais la liste, tu vois la liste du nouveau projet.

Le fichier ouvert se ferme ; le flux du run affiché réinitialise.

### Démarrer ou arrêter l'app d'une carte de projet

Quand un projet déclare une app, tu vois un bouton **Lancer** (ou **Arrêter** si elle tourne déjà) au bas de la carte.

Un clic démarre ou arrête l'app sans quitter la vue Projets ni sélectionner la carte — pratique pour lancer plusieurs projets d'affilée. Pendant l'appel, le bouton se désactive ; la carte se rafraîchit pour afficher le nouvel état.

En cas d'erreur, un message court s'affiche sous le bouton en rouge. La carte reste cliquable — tu peux relancer.

Aucun bouton n'apparaît si le projet n'a pas d'app.

Si un projet déclare un service (une API, une interface web, un outil), tu vois un bouton de contrôle sur sa carte.

**Démarrer** lance l'app. L'IDE affiche la sortie en console pour que tu voies le démarrage en cours. Le bouton devient **Arrêter**. Tu peux le reclicquer pour fermer l'app.

Si tu essaies de relancer une app qui est en train de démarrer, l'IDE attend qu'elle soit prête, puis la redémarre — sans risque de lancement double.

Les apps lancées par Tessera pendant un run du pipeline apparaissent aussi dans l'inventaire global avec l'origine **Tessera**.

### Changer la catégorie d'un projet

Chaque carte a un menu accessible (trois points verticaux). Clique dessus pour :
- Choisir une catégorie existante
- Taper une nouvelle catégorie
- Retirer la catégorie

La liste se recharge, et la barre latérale s'actualise.

### États de la vue

- **Chargement** : tu vois des cartes-squelettes gris clair
- **Erreur** : un message avec un bouton « Réessayer »
- **Aucun résultat** : un message et un bouton « Effacer la recherche »

### Les filtres survivent au changement d'onglet

Si tu cherches « api » et que tu tris par activité récente, puis que tu reviens à l'onglet Kanban et au Projets, tu retrouves les mêmes réglages.


### Accéder aux réglages

Les réglages globaux de l'IDE se trouvent dans un panneau accessible via un bouton en bas du rail de navigation (icône engrenage). Clic dessus ouvre un panneau où tu peux :

- **Autoriser ou désactiver les notifications** : par défaut, les notifications du navigateur sont désactivées. Tu dois les autoriser dans les réglages du site pour que Tessera puisse t'avertir.
- **Consulter et modifier tes plafonds de dépense** : dépense maximale par ticket et par file.

Ces réglages sont globaux — ils s'appliquent à tous tes projets, pas seulement au projet actif.

#### L'en-tête de colonne allégé

L'en-tête de colonne montre dorénavant uniquement ce qui concerne le projet actif :

- Le **sélecteur de projet** (dropdown avec le nom du projet)
- Une **pastille bleue** quand un run tourne sur ce projet
- La **ligne d'actions** : Services, VSCode, Git, Signaler

L'infobulle du sélecteur te dit « ce projet fait tourner l'IDE ».

Le panneau « Pipeline » du projet reste accessible depuis l'onglet Agents ou Tickets quand tu en as besoin.

## 2 ter bis. Surveiller les services

### Ouvrir la vue En cours

Tu cliques sur « En cours » dans la barre latérale, juste sous « Projets ».

Une pastille affiche le nombre d'apps vivantes — elle disparaît quand ce nombre 
vaut 0.

### Ce que tu vois

En tête, la mémoire totale consommée par toutes les apps.

Chaque app apparaît sur une ligne, groupée par projet, triée par mémoire 
décroissante (la plus gourmande d'abord). Pour chaque app tu vois son nom et 
celui de son projet, son origine (« Tessera » ou « Lancé à la main »), ses 
ports affichés en bleu et cliquables, la durée depuis son démarrage, sa mémoire 
en Mo, et un bouton « Arrêter ».

### Arrêter une app

Tu cliques sur « Arrêter ».

- **App lancée par l'IDE** : elle s'arrête immédiatement.
- **App lancée à la main** : une confirmation s'affiche d'abord.

La liste se met à jour aussitôt après.

### Mise à jour automatique

La vue se réactualise toutes les 10 secondes tant qu'elle est visible. 
Elle s'arrête si tu navigues ailleurs.

### États de la vue

- **Vide** : « Aucune app de projet ne tourne » — c'est normal, aucune app n'a 
  été lancée.
- **Chargement** : la liste est en cours de lecture.
- **Erreur** : quelque chose a échoué ; l'écran affiche le message.

## 2 ter. Vue « En cours »

La destination « En cours » vous permet de superviser toutes les apps de projet
en cours d'exécution sur votre machine — sans avoir à passer par chaque projet
pour voir qui tourne et qui consomme de la mémoire.

### Accéder à la vue

Dans la barre latérale (NavRail), cliquez sur « En cours », juste après « Projets ».
Une pastille affiche le nombre d'apps actives (absente si aucune ne tourne).

### Ce que vous voyez

**En tête** : la mémoire totale consommée par l'ensemble des services.

**Puis, par projet** : la liste des apps groupées et triées par mémoire décroissante.
Pour chaque app, vous voyez :

- **Nom du projet et du service**
- **Origine** : « Tessera » si lancée par l'IDE, « Lancé à la main » sinon
- **Ports** : affichés en liens cliquables (`http://localhost:8100`, etc.)
- **Durée** : depuis combien de temps elle tourne
- **Mémoire** : consommation en Mo
- **Bouton Arrêter**


**Les services sans port** — Chaque service écoute normalement un port réseau, affiché sous forme de lien (« 8000 », « 5173 »). Un service sans serveur réseau — par exemple `python -m app.worker` lancé sans option `--port` — n'a rien à écouter : tu vois « — » à la place du lien.

### Arrêter une app

Un clic sur « Arrêter » :
- Pour une app lancée par Tessera → arrêt immédiat
- Pour une app externe → demande une confirmation d'abord (« Arrêter le processus N ? »)

Après l'arrêt, la liste est rechargée automatiquement.

### Rafraîchissement

La liste se met à jour toutes les 10 secondes tant que vous restez sur cette vue.
Si vous la quittez, le rafraîchissement s'arrête pour économiser les ressources.

### États

- **Vide** : « Aucune app de projet ne tourne »
- **Chargement** : récupération de la liste en cours
- **Erreur** : un problème a empêché le chargement (vérifiez votre connexion)

### Arrêter un projet entier

Un bouton dans l'en-tête du groupe arrête toutes les apps du projet en un clic : d'abord les services Tessera, puis chaque app lancée à la main (identifiées par pid externe). S'il y a une app externe, une confirmation en affiche le(s) pid(s) avant d'aller plus loin.

Le bouton « Arrêter » par app seul lance l'arrêt sans confirmation — il arrête l'app individuelle, pas le groupe.

Après arrêt complet, le projet disparaît de l'inventaire.


« Arrêter le projet » arrête tous les services du projet, y compris ceux sans port. L'IDE les repère grâce à leur répertoire de travail : un `python -m app.worker` lancé dans un dossier concurrent ne sera pas arrêté.

### Feedback pendant l'arrêt

Dès que tu cliques, la ligne passe en « Arrêt… » avec un spinner. Les boutons se désactivent pour t'empêcher de lancer deux arrêts en même temps. Tessera cherche plus souvent si le projet a disparu, pour que tu voies la fin au plus tôt.

Si après 30 secondes un pid n'a toujours pas disparu, un message d'erreur s'affiche — l'app refuse peut-être de s'arrêter. Les boutons redeviennent cliquables ; tu peux relancer le projet ou l'arrêter à la main.

### Relancer un projet arrêté

Au-dessous de l'inventaire en cours, une section « Arrêtés » regroupe les projets qui déclaraient des services au lancement mais n'en tournent plus. Un bouton « Lancer » redémarre leurs services configurés.

Cliquer sur ce bouton montre « Lancement… » en attente (jusqu'à 30 s). Une fois ses apps redémarrées, le projet réapparaît dans la liste.

La section est repliée par défaut si le groupe compte plus de 5 projets — tu peux la déplier.



« Lancer » ne redémarre pas un service déjà en cours. Si le service s'était relancé avant le clic ou si l'arrêt était incomplet, « Lancer » détecte son processus et le laisse tourner.

### Applications externes et attribution au projet

Une app n'est attribuée à un projet que si le processus (ou son parent direct) exécute depuis le dossier du projet ou possède un répertoire de travail situé sous ce dossier. Les chemins sont résolus (symlinks suivis) et la casse ignorée sous Windows.

Si un port déclaré par le projet est occupé par un processus **étranger** — dont la ligne de commande et le répertoire ne sont pas sous le dossier du projet — ce processus n'est pas une app du projet. Il apparaît comme un **avertissement** : « port 8000 déclaré, occupé par un autre programme », sans bouton « Arrêter ». Tu ne peux pas l'arrêter depuis la vue « En cours ».

Le projet qui fait tourner l'IDE lui-même n'a jamais d'app externe dans son inventaire.

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


Si le ticket dépend d'un autre et que le serveur distant n'est pas accessible, le pipeline arrête le ticket avec une raison explicite. C'est voulu : un ticket qui dépend d'un autre doit partir d'une base à jour, qui contient le merge du prédécesseur. Le fetch distant est retenté jusqu'à trois fois ; après trois échecs, le ticket se bloque plutôt que de partir d'une base périmée.


Chaque ticket débute par un **en-tête YAML** — les champs `id`, `title`, `type`, `status`, etc. — suivi de son corps en Markdown.

En vue Rendu (la vue par défaut), cet en-tête s'affiche en **fiche clé/valeur** au-dessus du corps, un champ par ligne. C'est bien plus lisible que l'ancien affichage, où le `---` devenait une barre, tous les champs un seul bloc de texte, et le `---` de fermeture un titre.

En vue Source (Monaco), tu vois le fichier brut, frontmatter compris.


**Quand une dépendance n'est pas mergée (ticket-384)**

La file n'attend pas — elle s'arrête. Si le ticket A (que B dépend de) échoue à se merger, alors :

- A passe en statut `blocked`, avec le motif dans `memory/pipeline-log.md`.
- B n'est pas lancé.
- La file s'arrête : `[<projet>] file interrompue : <ticket-A> non mergé`.

Résolvez A (conflit, rebase, relance manuelle) avant de relancer la file.

### Critères d'acceptation obligatoires pour le code

Pour tout ticket `feat`, `fix` ou `refactor`, tu dois ajouter une section `## Critères d'acceptation`. C'est là que tu énumères les comportements ou résultats que le validateur vérifiera.

Si tu omets cette section, le pipeline refuse le ticket — le message te demande d'ajouter une section `## Critères d'acceptation`. Les tickets `chore` ou `docs` (mise à jour de documentation, maintenance) n'en ont pas besoin : ils sont approuvés d'office.

Chaque critère se note en ligne séparée pour que le validateur puisse les vérifier un par un :

Quand tu cites des fichiers entre backticks dans tes critères d'acceptation, l'IDE les cherche pour confirmer qu'ils existent. Un chemin comme `src/Button.tsx` ou une extension reconnue (`button.tsx`) sont vérifiés. Un nom de propriété comme `BRAND.name` ou `settings.github_token` n'est pas un fichier et n'est pas cherché — l'IDE l'ignore.


#### Dossiers cités dans les critères

Tu peux citer un dossier entre backticks dans un critère — avec ou sans `/` final — par exemple « la maquette est dans `design/maquette/` ».

Le validateur joindra la liste des fichiers du dossier et pourra vérifier qu'il existe et n'est pas vide. C'est pratique pour des critères comme « les assets sont à jour » : au lieu de citer chaque fichier, tu cites le dossier qui les contient.

Le validateur vérifie l'existence du dossier, pas son contenu. Pour un critère de contenu (« la classe X existe »), cite le fichier spécifique plutôt que le dossier.

### Fichiers qu'un agent ne peut pas modifier

Certains fichiers définissent le projet lui-même et restent hors d'atteinte des agents : `CLAUDE.md`, `CLAUDE.local.md`, `agents.json`, `.claude/`, `.github/workflows/`, `.git/`.

Si un critère d'acceptation exige d'en modifier un — par exemple « Ajoute une section dans `CLAUDE.md` » — le run **ne démarre pas**. Il s'arrête avant le codeur avec un message explicite :

> Le critère 2 demande d'écrire `CLAUDE.md`, que le pipeline refuse aux agents : à faire à la main.

Reformule le critère pour qu'il ignore ces fichiers, ou fais la modification à la main d'abord, puis relance le run.

**Note** : un critère qui cite juste le fichier (« d'après `CLAUDE.md`, ... ») marche normalement.


Ton script de vérification est aussi protégé en écriture. Si ton projet déclare `test_command` et désigne un fichier sur disque (par exemple `../scripts/verifier.py`), aucun agent ne peut le modifier — tu verras la tentative refusée avec un message clair. L'idée est d'empêcher un ticket d'affaiblir le test qui doit le juger.

Quand un ticket modifie la configuration des tests — `conftest.py`, `vitest.config.ts`, `eslint.config.js`, la clé `scripts` de `package.json`, ou les sections `[tool.pytest*]` et `[tool.mypy]` de `pyproject.toml` —, le reviewer en reçoit un avertissement au début de son message. À lui de vérifier qu'aucune étape de vérification n'a été retirée ou désactivée.

    ## Critères d'acceptation
    
    - [ ] La fonction `trier()` retourne une liste triée en ordre croissant
    - [ ] Elle gère les listes vides sans erreur
    - [ ] Elle supporte les nombres négatifs

Le `[ ]` n'est que du markdown lisible — c'est pour ta clarté, pas pour que l'IDE les transforme en cases à cocher.

## 3 bis. Filtrer et trouver les tickets

Une fois que tu as plusieurs tickets, tu veux souvent en retrouver un particulier. Le tableau mémorise tes filtres (type, priorité, agent, texte) — ils survivent même au redémarrage de l'IDE.

### Quand un filtre cache des tickets

Si tu vois peu de tickets et que le panneau Tickets n'est pas ouvert, il y a souvent un filtre ancien qui s'applique toujours. Le tableau affiche une ligne au-dessus des colonnes dès qu'un filtre est actif :

- Combien de tickets tu vois versus combien il y en a en total (« 4 tickets sur 297 »)
- Le nom de chaque filtre appliqué (type design · priorité high)
- Un bouton **Effacer les filtres** pour tous les enlever d'un coup

Un clic sur ce bouton remet les filtres à zéro — tu verras tous les tickets de nouveau.

### Les colonnes done et cancelled ne montrent que les 30 derniers tickets

Dans les colonnes **done** et **cancelled** du kanban, seules les 30 cartes avec les numéros les plus élevés sont rendues au départ — c'est une optimisation pour garder l'écran fluide quand le projet accumule des centaines de tickets terminés.

En bas de la colonne, un bouton te permet d'afficher la totalité.

Le compteur de la colonne (le nombre en haut) affiche toujours le total réel, même quand seules les 30 cartes récentes sont visibles.

**Les autres colonnes** — todo, in-progress, in-review, blocked — affichent tous les tickets, quel que soit leur taille.

**La recherche et les filtres s'appliquent avant la limite** : tu cherches un ticket ancien dans done ? Il s'affiche même s'il n'est pas parmi les 30 récents.

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


L'audit de sécurité vérifie uniquement les lignes que tu ajoutes. Si tu modifies un fichier qui contient déjà une faille de sécurité, elle ne t'arrête pas : elle est signalée au reviewer, mais n'a pas d'effet sur ton ticket. Tu n'es responsable que du code que tu écris.


**Attention** : un quota d'abonnement épuisé pendant l'audit ne cause pas un blocage d'audit — c'est un arrêt de file pour quota. La file s'interrompt gracieusement, le ticket repasse en `todo`, et le journal affiche « quota épuisé — reprise vers HH:MM ». Seuls les vrais problèmes de sécurité détectés dans le code causent un vrai blocage ici.

### Si le validateur refuse

Si tu as écrit un ticket `feat`, `fix` ou `refactor` sans section `## Critères d'acceptation`, le validateur refuse et te demande d'en ajouter une. C'est voulu : rien ne peut être validé sans critères d'acceptation.

Édite le ticket, ajoute ta section `## Critères d'acceptation` avec tes critères, et relance le pipeline sur le même ticket — il reprendra du validateur. Rien n'est perdu, rien ne bloque le ticket suivant.


Vérifie le journal du pipeline : tu y trouveras une ligne `validateur: fichiers cités joints : …` qui énumère les fichiers que le validateur a reçus. Si cette ligne mentionne les fichiers qu'évoque ton critère d'acceptation, le validateur les avait en entier. Un refus ne vient donc pas d'un manque de contexte, mais de son interprétation du contenu. Cela arrive surtout avec un modèle local (Ollama) : même avec le texte complet, il peut être strict ou se tromper.

### Relancer un ticket

Quand tu relances un ticket, sa branche précédente est réutilisée — tu ne perds pas le travail d'avant. Le pipeline la met à jour automatiquement si elle est en retard sur la base du projet, ce qui évite que des changements d'autres tickets n'y causent des conflits imprévus lors de la livraison.

Si le rebasage échoue, l'ancienne branche est renommée `stale/<ancien-nom>` pour que tu ne la perdes pas, et une branche neuve est créée à partir de la base actuelle. Le codeur repartira d'une base propre.


### Reprendre un run sur une branche déjà travaillée

Quand tu arrêtes et relances un run (quota épuisé, interruption, redémarrage d'une session), le ticket peut reprendre sur une branche qui porte déjà du travail : des commits ont été faits au-delà de son point de départ.

**Si le projet a un testeur actif**, Tessera optimise cette reprise :
- Le testeur s'exécute d'abord pour valider le travail
- Tests verts → la branche passe directement à l'audit, la revue, le validateur — le codeur n'est pas réappelé
- Tests rouges, erreur d'environnement ou délai dépassé → le codeur reprend son travail, avec le résultat des tests dans sa réponse

**Si le projet n'a pas de testeur** :
- Le codeur est appelé normalement : sans tests, rien ne prouve que le travail existant tient

Un refus du reviewer ou du validateur renvoie toujours au codeur comme d'habitude. Seul le premier tour peut être sauté si les tests passent.

#### Quand le codeur est relancé pour corriger un refus

Si le dernier run s'est terminé sur un refus — audit sécurité, ou critères non satisfaits du validateur — la reprise repart du codeur **même si les tests étaient verts**. Cela évite une boucle infinie où le même code serait renvoyé aux mêmes portes qui l'ont refusé.

Le codeur reçoit le motif du refus précédent en contexte pour guider sa correction.

**Cas où le codeur reste sauté** : si le run a été interrompu sans verdict final (redémarrage du backend, coupure réseau), la reprise suit le même chemin qu'avant — elle saute le codeur si les tests ont été verts à sa dernière tentative.

### Refus antérieur d'une porte

Si ton dernier run s'est terminé par un refus (audit de sécurité, validateur ou reviewer), la relance recommence par le codeur — **même avec des tests verts**. Le motif du refus lui est fourni pour corriger le problème.

C'est différent d'une simple interruption (redémarrage, coupure) : là, sans verdict, le codeur peut être sauté si les tests passaient. Mais après un refus, il faut une correction.

Le journal affiche « … — refus précédent : <porte>, codeur en premier ».

### Quand des tests échouent

Quand des tests échouent, le **résumé du test** affiché dans le journal est clair et lisible — « 1 failed, 455 passed » au lieu d'une ligne de warning confuse. Le codeur reçoit aussi le **détail de chaque échec** — le nom du test et l'assertion qui a échoué — pour corriger en un seul tour.

Au lieu de tourner à l'aveugle plusieurs fois, tu remarques que les tickets progressent plus vite.


Quand une commande de test enchaîne plusieurs outils (vitest suivi de pytest, par exemple), le rapport affiche l'étape qui a échoué — avec sa propre sortie. Tu vois immédiatement la raison du blocage, au lieu d'être trompé par le résumé d'une étape précédente qui avait réussi.



Si un test expire (dépassement de `test_timeout_s`), tous ses processus enfants — même ceux qui tournent toujours en arrière-plan — sont arrêtés immédiatement. Le run reprend son cours au lieu d'attendre indéfiniment.

## 4 bis. Ajouter des tickets à une file en cours

Pendant qu'une file s'exécute, tu peux ajouter des tickets supplémentaires sans attendre la fin — ils seront exécutés après les tickets actuellement en attente.

### Quand c'est utile

Tu lances une file de trois tickets. Pendant qu'elle tourne, tu découvres deux nouveaux tickets liés à traiter immédiatement. Plutôt que d'attendre la fin et d'en lancer une seconde, tu les ajoutes à la file en cours. Cela évite un double lancement et garde une trace claire — un seul run pour l'ensemble.

### Comment ajouter des tickets

Tu es sur l'écran du run (voir [Lire ce qui se passe](#5-lire-ce-qui-se-passe) plus loin). Tu vois une action pour ajouter des tickets à la file en cours. Tu donnes les ticket IDs séparés par des virgules. Ils s'exécutent après les tickets actuels, dans l'ordre indiqué.

### Ce qui ne peut pas être ajouté

- **Un ticket déjà dans la file** : on ne duplique pas un ticket.
- **Un ticket déjà fait** : s'il est `done`, il a déjà été livré — pas besoin de le relancer.
- **Un ticket avec dépendance manquante** : si un ticket que tu ajoutes dépend d'un autre, celui-ci doit être livré ou dans la file actuelle. Sinon, le run refuse l'ajout et explique quelle dépendance manque.
- **Une file terminée** : seules les files `en cours` acceptent des ajouts. Quand elle s'arrête, même partiellement approuvée, c'est fini — lance une nouvelle file.

Un ticket inexistant. Les tickets que tu viens de merger sur ta branche de base sont trouvés et acceptés normalement, même si le run n'a pas encore mis à jour son arbre de travail.

### Si l'ajout échoue

Tu vois le motif : doublon, déjà fait, ou dépendance manquante. Le run n'est pas modifié. Corrige le problème et réessaye.


### Limite : projets isolés par worktree

Si ton projet est configuré pour isoler chaque run dans son propre répertoire (clé `worktree` dans `agents.json`), les files ne peuvent pas s'y lancer. Seul un ticket unique (`mode: single`) s'accepte, un à la fois.

Cela veut dire :
- Tu ne peux pas ajouter des tickets à une file en cours sur ce projet
- Tu dois lancer chaque ticket isolément
- L'IDE refuse l'ajout avec une erreur 422

C'est une sécurité : le projet a besoin que chaque run soit complètement isolé du checkout, pour éviter les écritures par erreur là où elles ne doivent pas être.

## 4 ter. Proposer des tickets en arrière-plan

Pendant qu'un run est en cours, tu peux proposer de nouveaux tickets sans attendre la fin du run. Ils seront intégrés immédiatement, indépendamment du run actuel.

### Quand c'est utile

Un run travaille sur `ticket-001`. Tu te rends compte qu'il faut aussi traiter `ticket-002`. Tu ne peux pas créer `ticket-002` sur la même branche (elle est occupée par le run). Tu le proposes à la place — il sera créé sur une branche séparée et fusionné automatiquement.

### Comment faire

Depuis le volet de création de ticket du projet :
1. Remplis le ticket (frontmatter + corps)
2. Clique sur **Proposer** au lieu de **Créer**
3. Le ticket est validé et créé immédiatement, sans attendre

Si le frontmatter est invalide, la création refuse.

### Ce qui se passe

L'IDE ajoute le ticket sur une branche séparée, ouvre une PR et la fusionne (ou la laisse en attente selon la configuration du projet). Le run actuel n'est pas affecté.

### Limites

Tu ne peux pas proposer un ticket qui touche à `CLAUDE.md`, `agents.json`, `.github/workflows/`, ou `.claude/` — ces fichiers sont protégés. La proposition sera refusée sans rien pousser.

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


Quand tu vois la ligne « testeur: en attente d'un créneau de test » dans le log, cela signifie qu'un autre testeur utilise le créneau de tests (limité à `MAX_PARALLEL_TEST_RUNS` tests simultanés). Le testeur actuel attend son tour, mais cette attente n'affecte pas le timeout — seul le temps réel d'exécution du test compte.


**La préparation du worktree (si déclarée)**

Quand ton projet déclare une commande `setup` dans son `agents.json`, le worktree se prépare avant que le codeur commence. Tu vois cette étape dans le journal du pipeline : une ligne comme `[ticket-XXX] préparation: <commande> (<durée>, code <exit_code>)`. Par exemple : `[ticket-042] préparation: pnpm install (1 min 49 s, code 0)`.

Si la préparation échoue, le run s'arrête — aucun agent ne commence son travail, et tu vois un message d'erreur expliquant ce qui n'a pas marché. Si tu ne déclares pas de `setup`, cette étape n'apparaît pas.

### Quand une file s'arrête

Une file arrêtée par une exception (timeout, saturation de ressources, etc.) écrit une ligne dans le journal du pipeline : `[projet] file interrompue : motif de l'erreur`. Tu peux voir l'arrêt immédiatement dans l'IDE, au même endroit que les autres interruptions (refus d'audit, dépassement de budget, limite de session). Tu n'as pas besoin de chercher dans les logs du serveur.

Une file qui s'arrête prématurément — sur budget, ticket non approuvé, ou autre raison — est rapportée avec un statut `interrompu` (jamais `done`). La raison exacte est incluse, ce qui t'aide à comprendre ce qui s'est passé et comment relancer si tu le souhaites.


#### Arrêt pour quota épuisé

Quand le quota Claude de ton abonnement s'épuise, la file s'arrête gracieusement — y compris si c'est pendant l'audit de sécurité. Le journal affiche « quota épuisé — reprise vers HH:MM » (heure locale estimée), le ticket courant repasse en `todo`, et tu peux relancer la file une fois ton quota renouvelé. Ce n'est jamais un blocage d'agent : c'est un arrêt normal de ressource.

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


En haut de l'onglet Supervision, tu as aussi un menu « Fermer… » qui t'affiche le nombre de runs dans chaque catégorie : « Les terminés (3) », « Les bloqués (1) », « En erreur ». Tu cliques sur une entrée pour fermer tous les runs de cette catégorie en un coup. Une entrée avec zéro run est grisée. Le menu ne s'affiche que si au moins un run est clos.

Si tu avais sélectionné un run que tu fermes avec le lot, la Supervision bascule sur un run restant.

### Rouvrir un run terminé

Un run une fois terminé disparaît de la Supervision après un rechargement ou une fermeture de session. Mais tu peux le relire à tout moment depuis l'historique :

- Ouvre le panneau **Historique** (panneau de droite) — il liste les runs récents avec leur verdict et leur date
- Clique sur une ligne pour rouvrir la vue complète du run : étapes, cartes par agent (codeur, testeur, sécurité, reviewer, validateur), verdict final
- La vue rouverte est **en lecture seule** : pas de bouton pour arrêter le run, pas de champ pour envoyer un message à l'agent, pas de chrono qui avance
- Un bouton **Fermer** te ramène à l'historique

C'est utile pour vérifier les détails d'un run après coup — comment chaque étape s'est déroulée, pourquoi un ticket a terminé bloqué — sans relancer la machine.



La carte du run affiche maintenant l'**état de la PR** en temps réel, même après fermeture. Si tu as fermé le run pendant que la PR attendait la CI, tu reverras « PR #42 — en attente de CI » la prochaine fois. Une heure plus tard, en rouvrant le run, tu verras « PR #42 mergée ». Si la CI a rejeté la PR, l'IDE affiche le motif de blocage.

Tu peux donc suivre la livraison d'un ticket **après** le run, sans relancer le pipeline ni vérifier GitHub : ouvre juste la carte fermée.


Si tu recharges la page durant un run en cours, tu retrouves instantanément tout l'historique — plan, tours précédents, tous les agents qui ont déjà passé. Le frontend rejoue les événements enregistrés en base de données, sans perdre ni dupliquer aucun message. C'est une des sécurités de l'interface : un rechargement accidentel ne coûte rien.


Tu retrouves aussi un run depuis le panneau du ticket. Ouvre le ticket — le bouton « Voir le ticket » en haut du run fermé t'y mène — et clique sur « Revoir le run » pour afficher le déroulé complet : plan initial, tous les tours, verdicts du reviewer et du validateur.


Quand tu sélectionnes un ticket qui a des runs terminés, une bande « Runs de ce ticket » apparaît sous la fiche d'en-tête. Elle liste chaque run : son statut (approuvé, rejeté), la date, les tours complétés, le coût. Un bouton « Revoir le run » ouvre la vue en lecture seule du run, qui rejoue son déroulé entier — tous les événements, les verdicts étape par étape, exactement comme à l'époque. Fermer cette vue revient au fichier du ticket.

Un ticket sans run terminé ne montre pas de bande. Un fichier ouvert depuis l'arbre (par double-clic dans l'explorateur) n'en montre pas non plus.

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

Tu vois l'étape **Tests** dans la frise si ton projet a un testeur. Elle est verte quand la suite réussit, rouge si elle échoue. L'étape n'apparaît que si le projet a un testeur configuré.

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

Une carte **TESTEUR** s'ajoute au fil après chaque passage du codeur. Elle porte le résumé des résultats — `1 error in 2.32s` ou `all pass` — et, dépliée, le détail des erreurs. Si la suite est rouge, elle t'explique : **« retour au codeur, sans revue »** — c'est pourquoi l'étape Tests est rouge et que l'audit de sécurité et la revue ne tourneront pas ce tour.


#### Approuvés et arrêtés

Une file affiche les tickets en quatre groupes :

- **Approuvés** : tickets livrés (tous les rôles ont approuvé)
- **Arrêtés** : tickets bloqués (non approuvés), chacun avec son motif short : « testeur: délai dépassé », « reviewer: refusé », etc.
- **Restants** : tickets non encore lancés
- **Courant** : le ticket en traitement

Si un ticket est arrêté, son motif te guide pour le corriger et le relancer.

### Runs récents — chercher et afficher plus

Dans le cockpit ou l'onglet Supervision, une carte « Runs récents » affiche les dix derniers runs. Tu peux :
- **Chercher** : tape dans le champ en haut de la carte pour filtrer par numéro de ticket ou nom du projet. La recherche se lance automatiquement quand tu arrêtes de taper.
- **Afficher plus** : clique le bouton en bas pour ajouter 20 runs à la liste.

Sans action de ta part, la carte reste aux dix runs : elle ne fait aucun appel API en arrière-plan.


La bande « Runs de ce ticket » affiche tes trois runs les plus récents, triés du plus neuf au plus vieux. Seuls les vrais runs du ticket apparaissent : les enveloppes de file — qui portent l'id du premier ticket et rejouent les événements de la file entière — sont écartées. Un bouton « Afficher les N autres » déplie le reste. La bande est bornée en hauteur et défile si besoin, afin que le ticket lui-même reste lisible même après beaucoup de runs.

### Retrouver une file par son identifiant

Quand tu lances une file de tickets, l'IDE te rend un identifiant unique — par exemple `92571cf0d5f64a4a8b7d3c1e0f2a9b64`. Garde-le.

Avec cet identifiant, tu peux retrouver ta file à tout moment, même après redémarrage de Tessera ou plusieurs heures plus tard. Tu verras :

- Le ticket en cours de traitement
- Les tickets déjà faits
- Les tickets encore en attente
- L'heure de lancement et (si la file est terminée) l'heure de fin

C'est plus direct que de chercher ta file dans l'historique, notamment quand plusieurs files s'étalent sur le temps.


### Le journal du pipeline en bas

Le journal du pipeline s'affiche en bas de l'écran. Pour te laisser plus de place, il est **replié par défaut** ; tu peux le déplier quand tu veux voir tous les évènements.

**Panneau replié (par défaut)** — une barre de 32 px affichant :
- le mot « JOURNAL »
- une **pastille bleue** si un run tourne actuellement
- **le dernier évènement**, tronqué sur une ligne
- le bouton « Déplier ▴ »

Un clic sur la barre déplie le journal à 180 px, affichant la liste complète des évènements. Le bouton devient « Réduire ▾ ».

**L'état du panneau persiste** — le navigateur sauvegarde si tu l'as laissé replié ou déplié, tu le retrouves dans le même état quand tu reviens.

Quand le CIWatcher merge une PR après une CI verte, cet événement s'écrit dans le journal du pipeline du projet (`memory/pipeline-log.md`). Tu y vois une ligne : `[projet] ticket-XXX PR #N mergée (CI verte)`. Le journal devient donc ta source de vérité pour connaître ce qui a été livré, sans relancer l'IDE ni interroger GitHub.

### Cliquer sur un ticket pour l'ouvrir

Partout où tu vois un numéro de ticket dans Tessera — dans une file en cours (Supervision), dans l'en-tête d'un run, dans l'Historique — tu peux cliquer dessus pour ouvrir son détail dans l'onglet Tickets.

Si le ticket appartient à un autre projet, tu passes automatiquement sur ce projet avant d'ouvrir le détail.

Un ticket introuvable (supprimé ou renommé depuis) affiche un message au lieu d'une erreur.

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

### Si la phase 2 échoue (après le run)

La fusion se poursuit en arrière-plan, après que le run soit terminé. Si elle échoue — conflit de rebase, CI rouge, ou délai dépassé — tu ne resteras pas dans le doute : l'IDE te signale comment elle a fini. Le ticket passe en `blocked` avec la raison explicite.

Le travail du codeur est déjà commité sur la branche du ticket, et la PR est ouverte sur GitHub. Tu peux reprendre manuellement s'il y a un conflit simple, ou relancer le codeur si des modifications sont nécessaires.

### L'arbre revient propre

Un run terminé laisse toujours ton arbre git propre. La copie de travail revient sur la branche de base du projet (pas la branche du ticket), et aucune modification n'est laissée en vrac.

Tu peux lancer le ticket suivant sans nettoyer après toi. Le travail du run précédent reste sur sa branche dédiée (`ticket-XXX`) si tu veux le consulter plus tard.


Cela s'applique **même si le run n'a pas ouvert de PR** — que le run soit refusé à l'audit, interrompu, ou n'ait pas généré de changements. Le journal du pipeline est toujours commité sur la branche de base, et tu te retrouves sur cette branche, pas sur celle du ticket. La branche du ticket, elle, garde son dernier commit ; si tu dois relancer le ticket, tu auras à faire un `git checkout ticket-…` pour y revenir.

### Si une PR ne peut pas se fusionner

Une PR approuvée peut rester en attente de calcul de sa fusionnabilité chez
GitHub pendant plusieurs minutes — c'est normal après un autre merge sur la
même branche de base. L'IDE l'attend jusqu'à 5 minutes.

Si la PR reste non fusionnable après cette attente (conflit Git, règles de
branche, révisions manquantes), le merge échoue. Le ticket passe en `blocked`
et une ligne de log dans `memory/pipeline-log.md` explique pourquoi.

Les tickets dépendants d'un ticket bloqué refusent de démarrer — la file
s'arrête et t'affiche l'erreur.

Pendant l'attente de CI, si une PR devient non-fusionnable — par exemple à cause d'un conflit avec une autre branche — l'IDE arrête la surveillance aussitôt. Tu verras une ligne dans le journal `pipeline-log.md` signalant le problème : « PR #N en conflit avec <branche> » par exemple. Les tickets dépendants passent en échec.

### Conflits sur le journal fusionnés automatiquement

Dans une file, quand plusieurs tickets tournent d'affilée, chacun enregistre ses changements au journal du pipeline et à la documentation. Autrefois, tu devais arrêter la file quand le ticket suivant heurtait un conflit sur ces fichiers. Depuis, l'IDE les fusionne automatiquement—la file continue sans interruption. S'il y a aussi un conflit sur d'autres fichiers, tu dois approuver la résolution.



Les conflits du journal (`memory/pipeline-log.md`) et de la documentation (`memory/documentation.json`) sont résolus automatiquement en union — Tessera garde les ajouts des deux côtés. C'est utile quand plusieurs tickets sont livrés en parallèle et chacun ajoute ses logs et ses ids.

Les autres conflits restent bloquants et demandent une approbation.

### Conflits de rebase et résolution automatique

Lors de la livraison, si le rebase génère un conflit, Tessera tente automatiquement de le résoudre avec un agent spécialisé. Son travail est relu avant publication.

Si cet agent ne peut pas intervenir, la ligne d'arrêt t'en informe clairement : « résolveur non tenté : [raison] ». Le conflit reste alors non résolu dans la branche, qui ne sera jamais poussée. Tu peux arbitrer le conflit en local avant de relancer.



Quand deux tickets ajoutent chacun uniquement des modèles ou types au même `schema.prisma`, sans modification de bloc existant, Tessera fusionne les deux — tu n'as rien à faire. De même, si deux migrations Prisma ont le même numéro, celle du ticket est renommée au numéro libre suivant.

### Erreur réseau lors de l'ouverture de la PR

Si la réponse du serveur GitHub se perd lors de l'ouverture de la PR (timeout réseau), Tessera interroge GitHub pour retrouver la PR par sa branche et la confie au CIWatcher. Tu n'as rien à faire ; le workflow continue normalement et l'arbre reste propre.


### Quand tu mèrges une PR bloquée

Si un ticket reste `blocked` mais que tu mèrges sa PR manuellement (sur GitHub ou en ligne de commande), Tessera le détecte au prochain lancement de file ou de run autonome. Le ticket passe automatiquement en `done/` avec son `pr_number` renseigné. Tu verras une ligne de journal : « ticket-XXX rangé en done : PR #YYY mergée ».

### La branche a changé après approbation

Entre le moment où tu approuves et le moment du merge, la branche du ticket peut se modifier de deux façons.

**Les commits de rangement du pipeline** ne posent aucun problème — ce sont des ajustements internes : gestion des tickets en attente, mise à jour du journal. Tessera les reconnaît et laisse le merge s'achever.

**Un commit de code nouveau**, posé par une autre session ou un développeur direct, bloque le ticket. Le journal affiche « la branche a changé depuis l'approbation ». C'est intentionnel : ce que tu as approuvé n'est plus à la tête. Tessera refuse de livrer. Pour débloquer, tu relances le ticket — une nouvelle approbation vaut pour l'état présent de la branche. Ce n'est pas un retry automatique : un blocage pour cette raison est traité comme un problème qu'il faut relancer.

Ce verrouillage garantit que tes approbations restent valides jusqu'au merge.


Tessera retente plusieurs fois de lire la tête de la PR avant de conclure qu'elle a changé — c'est une protection contre les retards de l'API GitHub, qui peut prendre quelques secondes pour enregistrer un push. La plupart du temps, tout rentre dans l'ordre pendant cette fenêtre de relecture, et la PR se merge automatiquement. Seul un vrai changement de branche — quelqu'un a poussé un commit différent — refuse le merge immédiatement.

### Continuité après un redémarrage du backend

Après un redémarrage du backend, ta PR approuvée continue d'être surveillée automatiquement. Si la CI devient verte, le merge s'enchaîne sans intervention. Si la PR a déjà été mergée pendant l'interruption, le ticket passe automatiquement en `done`.

Note : les PR de résolution de conflit (quand Tessera corrige un conflit de rebase) ne sont pas reprises après redémarrage, car elles exigent une relecture avant merge.

Chaque reprise est notée dans le journal du pipeline (`memory/pipeline-log.md`).

Après un redémarrage du backend, Tessera cherche aussi les pull requests ouvertes dans le dépôt GitHub (pour les projets en `autonomy: merge` avec un dépôt configuré). Si une PR attend sa CI, elle sera de nouveau surveillée et mergée une fois que la CI passe — même si sa fiche est restée en `todo` localement. Rien n'est perdu.

Si ton projet n'a pas de dépôt GitHub ou si son autonomie est `pull`, Tessera reprend uniquement les tickets marqués `in-review` localement.

## 5 quart. L'onglet Historique

Tu consultes l'historique complet des runs de ton projet via l'onglet **Historique** (situé entre Tickets et Fichiers). Deux vues te permettent de naviguer dans cet historique.

### Deux vues : détail et tableau

Un sélecteur en en-tête te bascule entre :

- **Détail du run** (par défaut) : affiche un run unique et tous ses détails
- **Tous les runs** : affiche un tableau de tous les runs avec filtres optionnels

### Détail d'un run

En ouvrant l'onglet Historique, c'est d'abord la vue **Détail du run** qui s'affiche au centre. Tu y vois :

- L'identifiant et la date du ticket
- Son titre
- Le verdict (approuvé, refusé, bloqué) et le nombre de tours de la chaîne
- Un lien vers la pull request si elle a été ouverte
- Une rangée de chiffres clés : durée, coût, nombre de tours
- Le fil complet du run avec tous les événements et messages

**Sélection d'un run** : tu choisis quel run afficher en cliquant sur son entrée dans la colonne de gauche. Si aucun n'est sélectionné, le plus récent s'affiche.

**Aucun run** : si ton projet n'en a pas encore, le centre affiche « Aucun run sur ce projet ».

### Tous les runs : tableau et filtres

Bascule vers **Tous les runs** pour voir un tableau listant chaque run du projet : ticket, titre, verdict, tours, coût, date.

Tu peux filtrer ce tableau :

- **Tous** : chaque run sans limite
- **Approuvés** : les runs dont la chaîne a approuvé le travail
- **Refusés ou bloqués** : les runs stoppés ou rejetés
- **Plusieurs tours** : les runs avec plus d'un tour de révision

Un clic sur une ligne du tableau ouvre son détail.

#### Affichage des runs — pas de doublons

Chaque ligne du tableau représente un run de ticket. Quand une file contient plusieurs tickets — un run parent et plusieurs runs enfants —, le tableau affiche une ligne par ticket de la file, jamais le run parent lui-même. Un run d'un seul ticket (pas de parent, pas d'enfants) apparaît en une seule ligne.

#### Reconnaître un run interrompu

Un run arrêté par une veille système, un redémarrage ou un timeout s'affiche avec le badge « interrompu » et un tiret « — » à la place de la durée. C'est un run sans tour complété : tu verras zéro tour et le badge neutre « interrompu », jamais une durée aberrante.

## Notifications et historique du jour

La cloche en bas du rail de navigation regroupe toutes tes notifications du jour et te permet de les gérer et de les régler une par une.

### Accéder à la cloche

Clique sur la cloche en bas du rail. Une pastille **violette** affiche le nombre de notifications non lues. Pas de notification ? La pastille est vide.

La cloche s'ouvre en panneau avec deux onglets : « Aujourd'hui » et « Réglages ».

### L'onglet « Aujourd'hui »

Cet onglet affiche toutes les notifications du jour, de la plus récente à la plus ancienne. Les notifications non lues apparaissent en **gras**.

Un clic sur une notification t'ouvre le projet concerné — utile quand tu as plusieurs projets et que tu veux vérifier ce qui s'est passé pendant une absence.

Le bouton « Tout marquer comme lu » remet le compteur de la pastille à zéro.

L'historique s'efface à minuit (fin du jour). Le jour suivant, tu repartiras de zéro.

### L'onglet « Réglages »

Pour chaque type d'événement, deux cases à cocher :

- **Question** : un agent te demande confirmation
- **Figé** : un ticket passe en statut « figé »
- **Bloqué** : un ticket passe en statut « bloqué »
- **Terminé** : un ticket est livré et approuvé
- **Mergé** : un commit est mergé dans la base
- **CI rouge** : les tests d'une PR échouent, ou le merge est refusé
- **Quota bas** : ton crédit d'abonnement s'épuise

**Système** : l'événement s'affiche-t-il comme notification du système d'exploitation ? Activé par défaut.

**Son** : l'événement doit-il émettre un son ? Par défaut, seules la **Question** et la **CI rouge** sonnent.

### Ce que ça ne fait pas

- L'historique ne vit que dans ton navigateur — il ne remonte pas avant ton dernier chargement de l'écran.
- Les réglages sont **globaux** pour tous les projets, pas par projet.
- Le backend n'est jamais impliqué : notifications et réglages restent locaux.

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

### L'onglet Fichiers

Tu y lis et modifies ton code. Il affiche l'éditeur quand un fichier est ouvert, ou une page d'accueil quand aucun n'est ouvert — jamais la liste des tickets.

#### Mode Éditeur

L'éditeur est Monaco : coloration syntaxe, autocomplétion, tous les outils. C'est ton espace de lecture du code que l'agent a écrit, ou d'exploration du projet pour le prochain ticket.

#### Sans fichier ouvert

Tu vois trois choses :

- **Rechercher un fichier** — tape le nom d'un fichier, la liste se filtre à mesure. Clique pour l'ouvrir.
- **Fichiers du dernier run** — « Touchés par le dernier run — ticket-N ». Les lignes ajoutées sont en vert, les retirées en rouge.
- **Ouverts récemment** — tes 5 derniers fichiers, mémorisés par projet.

#### Mode Diff du ticket

En en-tête, un bouton te donne le choix : **Éditeur** (défaut) ou **Diff du ticket**.

En mode Diff du ticket, tu vois les modifications côte à côte (ancien à gauche, nouveau à droite) du ticket sélectionné. Sans ticket sélectionné, l'interface t'invite à en choisir un.

#### Raccourci Ctrl+P

Quand tu es dans cet onglet, Ctrl+P met le focus sur la recherche — ta façon d'ouvrir un fichier au clavier.

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

### Limites de budget et arrêt de file

Une file s'arrête proprement si le budget cumulé atteint son plafond (par défaut 5 $ × nombre de tickets) ou si ton abonnement atteint sa limite de session. Voir la section « Problèmes fréquents » pour les détails sur chacun de ces cas.

Dès que tu lances un run, ton PC reste éveillé — tes agents peuvent travailler toute la nuit. L'écran peut s'éteindre, mais la mise en veille du système est empêchée.

Sur Windows, c'est actif. Sur Mac et Linux, ça n'a aucun effet — on laisse juste le réglage pour la cohérence.

Tu peux désactiver ça si tu veux que ton PC dorme normalement, ou si un autre outil gère la veille pour toi : mets `KEEP_AWAKE_DURING_RUNS=false` dans `.env`.

Ça n'empêche pas Windows Update de redémarrer le PC, ni l'écran de s'éteindre.


### Limite : projets isolés par worktree

Le mode autonome — qui lance des tickets en séquence sans intervention — ne fonctionne pas sur les projets à worktree. Seul un ticket unique (`mode: single`) peut s'y lancer pour chaque run.

C'est la même sécurité que pour les files. Ces projets exigent que chaque run soit hermétiquement isolé du reste de ton arbre. Lance-les un par un avec un ticket `single`, ou retire la clé `worktree` de ta configuration si tu préfères traiter plusieurs tickets d'affilée.

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


#### Quand ta réponse arrive trop tard

Une question a une durée de vie : passé ce délai (cinq minutes par défaut), l'agent reprend seul en énonçant son hypothèse. Si ta réponse arrive après ce délai, elle n'est pas perdue.

Le backend la dépose comme message spontané — l'agent la trouvera au tour suivant et pourra la lire, même si la question a expiré. L'écran te dit ce qu'il s'est passé :

- **« Réponse transmise »** si elle a rejoint la question à temps
- **« Réponse déposée pour le tour suivant »** si elle est arrivée tard

Une question expirée s'affiche comme telle : **« Expirée à HH:MM »**, accompagnée de l'hypothèse que l'agent a énoncée pour continuer. C'est un signal : l'agent a poursuivi sans ta réponse, mais il lira ta réponse quand tu l'enverras, au tour suivant.

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

#### Fichiers protégés contre toute modification

L'agent ne peut modifier aucun des fichiers système ou de configuration protégés : `CLAUDE.md` (à la racine du projet), `agents.json`, les fichiers du dossier `.claude/`, `.github/workflows/`, ou `.git/`.

Si un ticket demande une modification de ces fichiers, l'agent la refuse et le rapporte clairement : ce qui a été demandé et pourquoi c'est hors de son périmètre. Un refus est **définitif** — l'agent ne cherche jamais un contournement par un script, `python -c`, ou une autre voie. Tu relises ce refus pour clarifier le ticket.

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

### Notifications de livraison

Après un run livré en autonomie ou approuvé, Tessera t'envoie une notification :

- **PR mergée** : annonce le numéro de la PR.
- **PR non mergée** : annonce la raison (« CI rouge, PR laissée ouverte », « merge refusé », etc.).

Comme toutes les notifications, aucune n'est envoyée si le projet actif est affiché et la fenêtre visible.

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


Les requêtes à Ollama sont **mises en file d'attente par serveur** — une seule à la fois par défaut. Cela élimine la compétition sur le modèle quand plusieurs runs demandent Ollama au même moment : chacun attend son tour, puis obtient une réponse à pleine vitesse.

Si tu as besoin d'augmenter le nombre de requêtes concurrentes (sur une machine très puissante, par exemple), configure `ollama_max_concurrent` dans ta configuration Tessera (défaut 1 ; à 0 ou moins pour désactiver cette borne).



Si le serveur Ollama est indisponible ou surchargé, les rôles basculent automatiquement et rapidement sur Claude. Tu n'as rien à faire.

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


#### Maquette d'interface — source de vérité visuelle

Si ton projet a une maquette, elle devient la source de vérité pour tout changement d'interface. Les agents reproduisent fidèlement sa structure, ses espacements, ses tailles et ses états — au lieu d'inventer une mise en page ou de refondre l'UI à chaque ticket.

**Créer une maquette** : tu la fais manuellement, hors du pipeline, seul(e) ou avec un designer, en utilisant l'éditeur de maquettes de Claude (artifacts). Sauvegarde-la en HTML dans `design/maquette/` — un ou plusieurs fichiers `.dc.html` par écran. L'éditeur génère le texte ; tu peux le versionner tel quel.

**Impact sur la charte** : ta charte `memory/design.md` se construit sur les couleurs et les patterns de la maquette. Quand un agent reproduit l'interface, il utilise les tokens de charte plutôt que des couleurs en dur.

**C'est optionnel** : un projet sans maquette marche aussi bien. L'agent propose une charte visuelle neuve — utile pour des chores ou des projets minimalistes. Tu peux ajouter une maquette plus tard.

Un projet créé depuis le gabarit FastAPI + React a un dossier `design/maquette/` vide et un `README.md` expliquant comment charger une maquette.

### Ce que le testeur attrape

Le testeur lance les mêmes outils que ta CI : `pytest` et `mypy` pour Python, `tsc` pour TypeScript, puis `eslint` et `vitest` pour le frontend. Un ticket n'échouera plus soudain en CI sur une erreur de typage ou de lint — le pipeline les détecte tous maintenant, avant même que la PR soit ouverte.

Si tes critères de test chaînent plusieurs étapes avec l'opérateur `&&` (par exemple, `npm run build && npm run test`), le testeur les lance une à une et s'arrête à la première qui échoue. C'est le seul opérateur supporté : `|`, `||`, `;`, `>`, `&` et les redirections sont refusés avec un message d'erreur.


### Observer les coûts et performances des rôles

L'onglet **Agents** te montre comment ton pipeline travaille et ce qu'il coûte.

Tu peux choisir entre deux vues : **Fiche** (la défaut) ou **Comparer**.

#### Fiche d'un rôle

La vue **Fiche** affiche le détail complet d'un rôle :
- **À gauche** : une phrase sur ce que ce rôle fait (extrait de sa description, ou première ligne du prompt), le prompt système intégral qu'il voit, et ses derniers verdicts quand il en produit (reviewer, validateur, sécurité).
- **À droite** : le modèle qu'il utilise (ex: Sonnet 5.5), le modèle de secours si le premier n'est pas dispo, et sur **les 30 derniers jours** du projet actif : nombre d'appels et coût total en dollars. S'il n'a pas travaillé pendant cette période, tu vois « — » au lieu d'un montant.

#### Comparer les rôles

La vue **Comparer** affiche tous les rôles actifs du projet dans un tableau : rôle, modèle, appels (30 jours), coût. Un clic sur une ligne bascule à la **Fiche** de ce rôle.

Ça te permet de voir d'un coup d'œil quel rôle consomme le plus ou est sollicité différemment que prévu.

### Skills spécialisés

Certains domaines ont des **skills** — des guides que les agents appliquent automatiquement quand c'est pertinent.

#### Skill `mise-en-ligne` pour les sites servis en ligne

Si ton projet est un site web, une PWA ou une application SaaS, les agents ont une checklist de mise en ligne couvrant une vingtaine de points essentiels souvent oubliés avant le lancement.

**Points clés :**

- Page 404 fonctionnelle et lisible
- CTA visible au-dessus du pli, collant en bas sur mobile
- Titre et meta description pertinents par page
- Image Open Graph présente
- Favicons sur tous les appareils
- `robots.txt` et `sitemap.xml` accessibles
- Alt descriptif sur chaque image
- Responsive : fonctionnel à partir de 375 px (width mobile min)
- États de chargement et d'erreur clairs
- Politique de confidentialité, mentions légales, adresse de contact
- Page de remerciement après chaque formulaire

**Consentement et traceurs :**

Tu n'as besoin d'un bandeau cookies que si tu utilises un traceur qui l'exige. Une mesure d'audience exemptée de consentement — Plausible, Umami, GoatCounter — dispense du bandeau. Sinon, ajoute `vanilla-cookieconsent`.

**Textes juridiques :**

Les agents proposent des gabarits marqués « À_REMPLACER ». Tu dois les relire et les valider toi-même : aucun agent ne peut les remplir définitivement.

**Implémentation selon ta stack :**

- React 19 + Vite : titres et meta dynamiques nativement, sans `react-helmet-async`
- Next.js : couvre `metadata`, `sitemap.ts`, `robots.ts`, `opengraph-image`, `not-found.tsx`

**Performance :**

Une fois déployé en production, une mesure Lighthouse CI valide vraiment sur l'URL réelle. Avant cela, un test Playwright vérifie : 404, robots.txt, sitemap.xml, og:image, CTA visible, aucune requête vers un traceur avant consentement.

Les agents utilisent ce guide pour trouver les points manquants et te proposer les corrections.

Le skill configure automatiquement ton site sur Vercel : création du projet, domaine, variables d'environnement, redéploiement.

Renseigne d'abord `VERCEL_TOKEN` dans `.env` (portée minimale : `read` sur projects, `write` sur deployments).

**Ce qu'il fait** :
- Crée ton projet Vercel s'il manque, sinon le réutilise
- Ajoute le domaine personnalisé si tu en as déclaré un
- Écrit les variables d'environnement `NEXT_PUBLIC_APP_URL`, `SESSION_SECRET`, `CRON_SECRET` si absentes — jamais de réécriture
- Redéploie uniquement si une variable a été écrite

**Si le jeton manque** — l'étape s'arrête en `needs_human`, en attendant que tu renseigues `VERCEL_TOKEN`.


Le skill `mise-en-ligne` prépare ton app pour le web : Vercel pour l'hébergement, Neon pour la base de données.

Tu n'as rien à configurer — Tessera crée tout automatiquement :
- Un projet Vercel (s'il n'existe pas)
- Une base de données PostgreSQL (s'il n'existe pas)
- L'URL de la base est injectée dans Vercel sous le nom `DATABASE_URL`

Après, ton app peut se connecter à sa base dès son déploiement.

**Le schéma de la base (tables, index, etc.), c'est à toi** — à ta première migration, avec un script SQL ou ton ORM.

**Si quelque chose existe déjà** :
- Base Neon du même nom → Tessera la réutilise (pas de recréation)
- `DATABASE_URL` dans Vercel → Tessera saute l'étape de base de données
- Deux bases du même nom → Erreur, à toi de nettoyer

**Sans clé API Neon** :
Configure `NEON_API_KEY` dans `.env` pour que la création soit automatique. Sans elle, tu dois copier-coller `DATABASE_URL` toi-même.


**Enregistrements DNS (Cloudflare)**

Quand tu mets un site en ligne, Vercel et Resend te demandent des enregistrements DNS. L'IDE les crée automatiquement chez Cloudflare, à condition que la zone existe déjà — l'achat du domaine et son ajout à Cloudflare restent humains.

Tu n'as qu'à renseigner `CLOUDFLARE_API_TOKEN` (avec les droits d'édition sur ta zone) et à déclarer la zone dans la configuration du projet.

S'il manque un enregistrement et que tu as les droits, l'IDE le crée. Si tu en as modifié un manuellement (même type et nom, contenu différent), l'IDE s'arrête et te le signale — il n'écrase jamais. Si la zone n'existe pas chez Cloudflare ou que le jeton manque, l'IDE te donne la liste de ce que tu dois créer à la main.

L'IDE n'efface jamais d'enregistrement, même s'il n'en a pas besoin.

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

L'IDE refuse de lancer si ton arbre contient des fichiers modifiés en dehors du pipeline — un `agents.json` changé dans l'écran Agents, ou un journal de pipeline en attente. Le Pipeline log affiche les chemins bloquants, par exemple : « l'arbre contient des modifications hors pipeline : agents.json, tickets/in-progress/ticket-007.md ». Tu **commites** ces fichiers s'ils sont volontaires, ou tu les **annules** (`git restore`) avant de relancer le ticket.

### Le pipeline tourne mais rien ne change dans les fichiers

Vérifie `LLM_PROVIDER`. Seul le mode `agent_sdk` donne les outils fichier au codeur.

### Des `500` inexplicables, et un port 8100 impossible à libérer

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

### L'agent refuse une modification de fichier système

Si un rapport d'agent indique qu'une modification a été refusée — par exemple, une tentative de modifier `CLAUDE.md`, `agents.json`, `.claude/`, `.github/workflows/`, ou `.git/` — c'est intentionnel. Ces fichiers sont des garde-fous que l'agent ne peut pas franchir.

Relire le ticket : demandait-il vraiment cette modification, ou y a-t-il une approche différente ? Si tu dois absolument faire cette modification, c'est une tâche manuelle — pas un travail d'agent. Les agents n'essaient jamais de contourner ce refus par une autre méthode. Un refus de ce type est définitif.

### Les tests échouent alors qu'ils passent chez moi

Le testeur lance la commande configurée dans le pipeline du projet, depuis la racine
du projet, avec un timeout de 120 s.

---


**Panne d'environnement vs. test échoué**

Le testeur peut s'arrêter sur deux raisons différentes :

- **Panne d'environnement** : un outil que l'étape appelle (tsc, vitest, next…) n'a pu démarrer. Le message le nomme. C'est généralement `node_modules` cassé — un lien symbolique mort (fréquent après un renommage de dossier), des dépendances manquantes ou mal installées. **Tu ne dois pas corriger le code.** Réinstalle les dépendances (`pnpm install --frozen-lockfile` ou `npm install`) depuis la racine du projet, puis relance le ticket.
- **Test échoué** : un test a démarré normalement mais a échoué, ce qui signale une erreur dans le code à corriger.

Le message du testeur l'indique clairement : il dit « panne d'environnement » si c'est une absence d'outil, ou affiche le test cassé sinon.

### La PR s'est ouverte mais le ticket passe en `blocked`

Tu vois la PR ouverte sur GitHub, mais le ticket passe en `blocked` — la phase 2 de la livraison (attente CI, merge) a échoué. La raison est indiquée : conflit de rebase, CI rouge, ou délai dépassé.

Le travail du codeur est toujours sur la branche du ticket, commité et poussé. Rien n'est perdu.

### Une file s'arrête en disant qu'une dépendance n'a pas été livrée

Tu as lancé plusieurs tickets en file, certains avec `depends_on : [...]`, et la file s'arrête sur un message du type : « ticket-003 dépend de ticket-002, qui n'a pas été livré : … ».

Cela signifie que ticket-002 a été approuvé, mais **sa livraison n'a pas atteint la branche principale du projet**. Elle s'est arrêtée avant l'ouverture d'une PR (conflit de rebase, erreur API, autonomie insuffisante). Ticket-003, qui dépend de son code, ne peut pas partir sur une base incomplète : la file s'arrête plutôt que de laisser ticket-003 tomber sur des tests rouges ou du code qui n'existe pas encore.

**Ce qu'il faut faire :**

1. **Vérifie le journal du pipeline** du ticket qui n'a pas livré — cherche « livraison » ou « rebase ». Il te dit pourquoi ça s'est arrêté.
2. **Corrige la cause** : jeton GitHub expiré, conflit non résolu, autonomie insuffisante…
3. **Relance la file** à partir du ticket arrêté.

La file ne se relance pas toute seule : il faut que tu corriges la cause d'abord.


C'est que la PR du ticket dépendant n'a pas pu fusionner. Regarde le log du
projet (`memory/pipeline-log.md`) — il te dit pourquoi : conflit Git, règles
de branche, révisions manquantes, ou autre blocage sur le dépôt.

Le ticket bloqué passe automatiquement en `blocked` (visible dans la colonne).
Corrige le problème sous-jacent, relance le ticket bloqué, et la file reprendra
à partir du ticket qui l'attendait.

### « Agent silencieux depuis X secondes »

L'IDE a stoppé cet agent parce qu'il n'émettait rien depuis trop longtemps. C'est **auto-géré** : le run reprend avec un fallback (Ollama ou fermeture gracieuse). Rien à faire.

Pour allonger le délai avant arrêt, modifie `agent_silence_max_s` dans la configuration (défaut 1200 s).


Tessera t'envoie aussi une notification dès qu'un agent ne produit aucun événement pendant plus de 3 minutes : c'est le signal « agent figé ». Si tu la reçois, l'agent est bloqué. Regarde le fil du run pour voir où il s'est arrêté.

### Une file s'arrête sur son plafond de budget

Une file peut s'arrêter avant de traiter tous ses tickets si la dépense cumulée atteint le plafond fixé. Par défaut, ce plafond = nombre de tickets × 5 $. Une file de 3 tickets peut donc coûter jusqu'à 15 $.

Si tu veux fixer une limite stricte (par exemple 10 $ pour une file de 3 tickets), déclare-la quand tu lances la file — le paramètre `budget_usd` remplace alors le calcul automatique.

Quand une file s'arrête sur le budget, le log affiche `[<projet>] file interrompue : plafond de dépense` et l'interface confirme l'arrêt. Les tickets non lancés restent en `todo`.


**Depuis octobre 2026** : en file, deux limites s'appliquent :
- Chaque ticket a son propre budget (15 $ par défaut). S'il le dépasse entre ses tours, il repassera en `todo` — tu le relances après.
- La file elle-même a un budget global (le cumul de tous les tickets). Quand il est atteint, la file s'arrête et affiche son coût : « file interrompue : plafond de dépense (15,24 $ / 15,00 $) ».

Avant cette date, un ticket pouvait être coupé parce que ses prédécesseurs avaient trop dépensé. À présent, chaque ticket se mesure à son propre budget — tu ne paieras jamais pour les autres.

### Une file s'arrête pour « limite de session »

Quand ton abonnement Claude atteint sa limite de session (« You've hit your session limit »), la file s'arrête avant le prochain ticket. Le ticket en cours repasse en `todo` — aucun n'est endommagé. Le log affiche `[<projet>] file interrompue : limite de session (reprise : <heure>)` et l'interface affiche l'heure à laquelle ton abonnement se réinitialise. Relance ta file après cette heure.

Contrairement aux autres arrêts, celui-ci ne marque aucun ticket en `blocked`.

### Un run s'est arrêté avant d'être livré (backend redémarré)

Si le backend s'arrête avant de finaliser la livraison d'un ticket approuvé, au redémarrage tu vois :

- Tous les fichiers que le codeur a créés pendant le run sont restaurés
- Le ticket reste en état « approuvé/done » au lieu d'être repassé en `todo` — tu vois une note dans le journal : « [ticket-XXX] approuvé mais non livré : livraison à reprendre »

**Attention** : un fichier créé accidentellement par toi pendant le run — un brouillon, un `.tmp` — sera aussi restauré dans la branche. Il sera visible dans la PR ; nettoie-le avant de merger.

### Un run refuse de démarrer (erreur 422)

Avant de lancer, Tessera vérifie que tu peux aller jusqu'au bout de la livraison et des tests.

**Vérifications pré-run :**

- **`github_remote` absent** : tu veux créer une PR (`autonomy: pr` ou plus), mais ton projet n'est pas lié à un dépôt GitHub.
- **CI absente** : tu veux fusionner (`autonomy: merge`), tu n'as aucun fichier `.github/workflows/*.yml` et tu n'as pas déclaré `merge_without_ci: true`.
- **Commande manquante** : ton `test_command` demande une commande (`pytest`, `npm test`, `cargo test`…) qui n'existe pas sur ta machine — le message énumère laquelle.

**Solutions :**

L'erreur énumère exactement ce qui manque. Ajoute-le :
- Renseigne `github_remote` pour lier à GitHub.
- Crée un workflow GitHub Actions, ou pose `merge_without_ci: true` dans la configuration du projet.
- Installe ou corrige la commande de test.

Après correction, relance. Si tu veux contourner ces vérifications — par exemple pour tester un ticket sans le livrer — passe `force: true` au lancement (détail en fonction du mode de requête utilisé).

### L'IDE signale un avertissement : « project_id différent du dossier »

Quand tu ouvres un projet, l'IDE vérifie que le `project_id` déclaré dans `agents.json` correspond au nom du dossier qui le contient. Si ce n'est pas le cas — par exemple après un renommage du dossier — tu vois un avertissement dans la vue d'ensemble du projet.

C'est normal et inoffensif, mais tu dois corriger : ouvre `agents.json` du projet et change `"project_id"` pour qu'il corresponde au nom du dossier. Tu peux aussi omettre le champ entièrement ; l'IDE utilisera le nom du dossier par défaut.

Exemple :
- Avant : dossier `devinoo`, mais `"project_id": "make-your-call"` → avertissement ⚠️
- Après : dossier `devinoo`, et `"project_id": "devinoo"` → pas d'avertissement ✅

L'avertissement disparaît une fois que tu as corrigé `agents.json` et relancé l'IDE.

### Un agent refusé par le CLI : « The user doesn't want to take this action »

Tu vois dans le journal du pipeline : `codeur: outil <nom> refusé par le CLI`

Cela signifie que le CLI embarqué a refusé un appel d'outil du codeur, avec le message exact : « The user doesn't want to take this action right now. STOP what you are doing and wait for the user to tell you how to proceed. »

La cause n'est pas établie — cela peut être un problème de permissions du CLI embarqué, ou un comportement inattendu. Le tour s'est arrêté sans progrès, et l'agent n'a rien produit dans ce tour.

Pour l'instant, il n'y a pas de correction automatique. Tu dois relancer le ticket. Si le problème reproduit régulièrement, note le `run_id` et signale-le sur Tessera via la section 13 « Signaler un problème ou une idée sur Tessera ».

### Le push est refusé : secret détecté

Avant d'ouvrir une pull request, Tessera scanne le diff ajouté pour détecter les secrets reconnaissables. Si un secret est trouvé, le push est refusé — le message d'erreur nomme le fichier et la ligne, mais jamais la valeur du secret.

Les secrets détectés incluent clés AWS, tokens GitHub/GitLab/Anthropic, clés privées (fichiers `.pem`, `id_rsa`), identifiants dans une URL (`user:password@host`), et l'ajout de fichiers de configuration (`.env`, `*.pem`, `id_rsa`).

Ce contrôle s'applique quel que soit le réglage `confidentialite` du projet.

Si c'est un faux positif — une URL de documentation, une chaîne placeholder — supprime la ligne et relance le pipeline.

## 13. Signaler un problème ou une idée sur Tessera

Quand tu trouves un dysfonctionnement dans l'IDE ou une suggestion pour l'améliorer, tu peux le signaler directement depuis n'importe quel projet — sans quitter l'IDE, sans naviguer jusqu'à ide-core.

### Accéder au formulaire

En haut de chaque projet (dans l'en-tête du sidebar), à côté des boutons Services, VSCode et Git, tu trouves le bouton **Signaler**. Un clic l'ouvre.

Ce bouton n'apparaît que si tu as un projet ouvert. Il est volontairement absent quand tu consultes ide-core lui-même.

### Remplir le signalement

La modale te demande :

- **Nature** : Bug (dysfonctionnement observé) ou Idée (suggestion d'amélioration)
- **Titre** : un résumé court et explicite
- **Description** : le contexte, les étapes pour reproduire (si c'est un bug), ou la suggestion détaillée

Le bouton d'envoi reste grisé tant que le titre ou la description sont vides.

### Après l'envoi

Un clic crée un ticket dans ide-core, associé au projet d'où tu signales. Tu vois tout de suite le numéro du ticket : **Signalé : ticket-NNN**.

Si l'envoi échoue (pas de connexion au backend), tu vois un message d'erreur. Ton texte reste en place — tu peux corriger et renvoyer sans rien perdre.


#### Quand un run ide-core est en cours

Si un signalement arrive pendant qu'une file ide-core tourne, il n'est pas converti en ticket immédiatement : il attend dans une file d'attente temporaire. L'interface affiche « En attente (position : 2) » au lieu d'un numéro de ticket. Le signalement devient un ticket normal dès que le run de ide-core se termine et se fusionne.


- **Défaut** : le signalement devient immédiatement un ticket dans ide-core.
- **Si un run ide-core tourne** : le signalement est mis en attente hors du dépôt. Il deviendra un ticket une fois le run terminé, protégeant ainsi l'intégrité du travail en cours.

### Les tickets ne sont visibles que dans ide-core

Les signalements créés ne remontent pas dans une liste locale. Tu les lis dans le Kanban d'ide-core, comme n'importe quel autre ticket de ce projet.

## 14. Mise en ligne d'un projet

Tu peux configurer l'IDE pour mettre en ligne ton projet : créer une base de données, configurer le domaine et ses enregistrements DNS, et déployer sur un hébergeur.

Le bloc `online` de ta configuration déclare les services à configurer (Neon pour la base, Resend pour l'email, Cloudflare pour le DNS, Vercel pour le déploiement). L'IDE exécute alors un plan d'étapes : créer la base, vérifier Resend, publier le DNS, puis déployer.

### Organisation Neon gérée par Vercel

Si ton compte Neon est lié à Vercel, il se peut que ton organisation Neon soit **gérée par Vercel**. Tu le vois dans les paramètres Neon : le champ `managed_by` affiche `"vercel"`. Dans ce cas, tu ne crées pas de bases via l'API de Neon — tu les crées depuis le tableau de bord Vercel.

L'IDE le détecte au moment du provisioning. L'étape « Base Neon » s'arrête avec une instruction claire au lieu d'un échec :

> Organisation Neon gérée par Vercel : dans Vercel, projet *<id>* › Storage › Create Database › Neon, en reliant Production et Preview. La relance lira DATABASE_URL.

Tu procèdes ainsi :
1. Va dans ton projet Vercel
2. Clique sur **Storage › Create Database › Neon**
3. Relie les branches **Production** et **Preview**
4. Reviens relancer l'étape dans l'IDE

Elle lira alors `DATABASE_URL` depuis Vercel et continuera comme prévu.

### Domaine www

Quand tu mets un projet en ligne, l'IDE configure automatiquement le sous-domaine `www` pour rediriger vers le domaine nu. Si tu publies sur `example.com`, l'IDE ajoute `www.example.com` qui redirige vers `example.com` — aucune action manuelle. L'enregistrement DNS et la configuration chez Vercel sont faits automatiquement.

Si tu as déjà un `www` avec une autre configuration, l'IDE le laisse inchangé.

### Mettre en ligne depuis l'IDE — suivi étape par étape

Un projet configuré pour la mise en ligne dispose d'un bouton « Mettre en ligne ». Clique-le pour lancer et suivre chaque étape du déploiement en temps réel.

#### Déclarer ton projet pour la mise en ligne

Dans la configuration du projet (`agents.json`), ajoute un bloc `online` avec le domaine et les services à déployer. Dès que tu sauvegardes, l'IDE affiche le bouton « Mettre en ligne » sur la fiche du projet.

#### Lancer la mise en ligne

Clique le bouton. Une modale te demande de confirmer deux choses :
- Le domaine sur lequel tu vas mettre en ligne
- Le mode Stripe : `test` (sandbox) ou `live` (production)

Revérifie (surtout le mode Stripe si tu déploies en production). Clique « Confirmer ». Le bouton se désactive pendant que les étapes s'exécutent, et tu vois la progression en temps réel.

#### Les sept états d'une étape

Chaque étape de la mise en ligne peut être dans l'un de ces états :

- **`todo`** : en attente
- **`pending`** : en cours
- **`done`** : complétée
- **`skipped`** : non applicable à ton setup
- **`manual`** : tu dois faire une action toi-même
- **`needs_human`** : pareil, mais lancée automatiquement
- **`failed`** : erreur

Les couleurs suivent l'ADR-026 de Tessera.


Le dry-run consulte l'état **actuel** auprès de chaque fournisseur (Resend, Vercel, Neon, etc.), sans rien modifier. L'étape de vérification de domaine chez Resend passe par plusieurs états avant d'être complètement validée :

- **À lancer** : aucune demande de vérification n'a encore été soumise
- **En attente** : la vérification a été lancée et les enregistrements DNS se propagent (MX et TXT). C'est l'état le plus courant après la première tentative. Attends que la propagation DNS complète.
- **Échoué** : la configuration du domaine n'est pas valide, ou l'une des vérifications a été refusée — corrige et relance la vérification

Si le dry-run affiche « En attente » pour le domaine, tu dois attendre la propagation DNS avant la mise en ligne. Vérifie l'état des enregistrements auprès de ton registrar ou d'un vérificateur DNS avant de relancer le dry-run.

#### Ce que tu dois faire : `manual` et `needs_human`

Quand une étape porte l'un de ces états, tu vois un bloc de détails. Lis-le. On peut te demander :
- **Enregistrements DNS** : crée-les chez ton registraire avec les valeurs exactes données
- **Ressources à créer** : une redirection de domaine chez Vercel, une clé API chez Stripe, etc.
- **Vérification** : confirme qu'une ressource est bien active avant de continuer

Exécute les actions demandées et reviens si nécessaire. Aucun jeton, clé secrète ou identifiant sensible ne s'affiche dans Tessera — tu les gères par le dashboard de chaque service, comme d'habitude.

#### En cas d'erreur

Une étape échoue ? Tu le vois immédiatement. Un message court te dit pourquoi. Le bouton se réactive. Tu peux relancer le plan quand tu es prêt. Les étapes déjà `done` seront sautées ; seule l'étape `failed` et ses dépendantes seront rejoués.

Vérifie ce qui n'a pas marché (config manquante, service indisponible, permissions insuffisantes) et relance.

## Pour aller plus loin

- [`architecture.md`](architecture.md) — comment Tessera est construit
- [`ticket-strategy.md`](ticket-strategy.md) — comment découper un backlog
- `projects/ide-core/memory/decisions.md` — les ADR, dont **ADR-017** (couche LLM) et
  **ADR-018** (isolation git du pipeline)
