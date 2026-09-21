---
id: ticket-099
title: "Renommer vibe-ide en Tessera, dépôt GitHub compris"
type: chore
status: done
pr_number: 90
priority: medium
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-21
---

# ticket-099 — Renommer vibe-ide en Tessera, dépôt GitHub compris

## Objectif

Remplacer `vibe-ide` / `vibe_ide` par `Tessera` / `tessera` partout où le nom
est un identifiant, un chemin ou un texte affiché — code, état local, shell
desktop, outillage, CI, consignes, documentation et dépôt GitHub — sans changer
le comportement du produit.

## Contexte

`vibe-ide` était un nom de travail. Le produit sort de sa phase bootstrap
(quatre-vingt-dix-huit tickets livrés, pipeline complet, livraison automatique)
et le nom ne tient plus la comparaison avec ce qu'il désigne.

**Tessera** : jeton d'admission à Rome, et carreau de mosaïque. Un ticket, et
une pièce de l'ensemble qu'il contribue à former.

Le nom est occupé sur les registres de paquets — PyPI (`tessera`, un front
Graphite abandonné vers 2016), npm (`tessera`, un serveur de tuiles
cartographiques), crates.io (`tessera`, 300 téléchargements) — mais par des
projets morts ou sans rapport, et aucun n'est un IDE ni un produit IA. Comme le
dépôt reste privé et qu'aucune publication sur ces registres n'est prévue, les
identifiants restent nus : `tessera`, sans suffixe.

391 fichiers portent le nom, hors `.git`, `node_modules`, `.venv` et
`projects/` : 351 dans `backend/`, 13 dans `frontend/`, le reste réparti entre
`docs/`, `agents/prompts/`, `.claude/`, `Makefile`, `docker-compose.yml`,
`.github/`, `.env` et `README.md`.

Ce n'est pas un `sed` global. Quatre catégories d'occurrences se comportent
différemment, et les confondre casse l'installation locale sans qu'aucun test
ne le voie.

## Solution proposée

Six lots, dans cet ordre. Chaque lot laisse le dépôt dans un état où
`make test` et `make lint` passent.

### Lot 1 — package Python

- `backend/src/vibe_ide/` → `backend/src/tessera/`
- `backend/pyproject.toml` : `name`, `packages`, `[tool.coverage] source`
- tous les imports `vibe_ide.*` → `tessera.*`, code et tests
- `backend/Dockerfile`

### Lot 2 — état local

Ces valeurs désignent des fichiers et des dossiers **qui existent déjà sur la
machine**. Les renommer dans le code sans déplacer l'existant repart d'un état
vide, en silence.

- `config.py` : `ide_db_path`, `vibe_ide.db` → `tessera.db`
- `config.py` : `ide_workspace_dir`, `~/vibe-ide-workspace` → `~/tessera-workspace`
- `project_removal.py` : `_DETACHED_DIRNAME`, `vibe-ide-detaches` → `tessera-detaches`
- `git_link.py` : identité git, `vibe-ide@localhost` / `vibe-ide` → `tessera@localhost` / `tessera`

Le rapport final du ticket doit lister les trois renommages à faire à la main :
`backend/vibe_ide.db`, `~/vibe-ide-workspace/` si le dossier existe, et
`vibe-ide-detaches/` à la racine.

### Lot 3 — frontend et shell desktop

- `frontend/src/` : textes affichés, types, clés de stockage éventuelles
- `frontend/src-tauri/Cargo.toml` : `name`, `description`, `lib.name` (`tessera_lib`)
- `frontend/src-tauri/tauri.conf.json` : `productName`, `identifier`
  (`com.tessera.app`), `title` de la fenêtre
- `frontend/src-tauri/src/lib.rs` et `main.rs`
- `Cargo.lock` régénéré par `cargo check`, jamais édité à la main

### Lot 4 — outillage et CI

- `Makefile` — cibles `dev`, `run`, `run-windows`, `stop`, `test`, `doctor`
- `docker-compose.yml` — service et volume `vibe-data` → `tessera-data`
- `.github/workflows/ci.yml`
- `.gitignore`
- `.env.example` — commentaires et chemins d'exemple
- `scripts/vibe.ps1` → `scripts/tessera.ps1`

### Lot 5 — consignes, prompts et documentation

**Ce ticket autorise explicitement la modification de `CLAUDE.md`** (règle 5),
de `projects/ide-core/CLAUDE.md` et de `projects/ide-core/memory/decisions.md`.

- les deux `CLAUDE.md`
- `memory/decisions.md` : le nom apparaît dans ADR-021, ADR-023, ADR-024,
  ADR-028 et ADR-031 comme **contrainte en vigueur**, pas comme trace
  historique — il se renomme. Le reste du texte des ADR ne bouge pas.
- un ADR court acte le nom et la décision de ne pas réserver les identifiants
  sur les registres publics — skill `write-adr`, budget de longueur compris
- `agents/prompts/*.md` — six prompts concernés
- `.claude/skills/run-vibe-ide/` → `.claude/skills/run-tessera/` et
  `.claude/commands/run-vibe-ide.md` → `run-tessera.md` : la slash command
  devient `/run-tessera`
- `.claude/skills/ticket-workflow/` et `.claude/skills/verification-before-completion/`
- `docs/architecture.md`, `docs/guide-utilisateur.md`, `docs/ticket-strategy.md`,
  `README.md`

`docs/superpowers/plans/` et `docs/superpowers/specs/` sont des plans **datés**
qui enregistrent un état passé : ils gardent le nom de l'époque.

### Lot 6 — GitHub

Le renommage du dépôt `BenjaminCharmes/vibe_ide` → `BenjaminCharmes/tessera`
est une **étape humaine**, faite depuis l'interface GitHub. Un agent n'y touche
pas : ADR-027 lui interdit les commandes git en écriture, et renommer un dépôt
distant est une action sortante qui appartient à son propriétaire.

Ce que le ticket produit pour cette étape :

1. la marche à suivre dans le rapport final — GitHub conserve les redirections
   depuis l'ancien nom, et les PR ouvertes comme les issues survivent au
   renommage
2. la commande de mise à jour du remote local :
   `git remote set-url origin https://github.com/BenjaminCharmes/tessera.git`
3. la vérification que `develop` et `main` poussent toujours après coup

## Critères d'acceptation

- [ ] `grep -ril "vibe" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=projects --exclude-dir=target --exclude-dir=dist --exclude-dir=superpowers .` ne renvoie aucun fichier
- [ ] `backend/src/tessera/` existe et `backend/src/vibe_ide/` n'existe plus
- [ ] `cd backend && uv run pytest -q -m "not integration"` passe, avec le même nombre de tests qu'avant le ticket et zéro échec
- [ ] `cd backend && uv run mypy src/` passe sans erreur
- [ ] `cd frontend && npm run build` passe sans erreur
- [ ] `cd frontend/src-tauri && cargo check` passe sans erreur
- [ ] `backend/tests/test_consignes_coherentes.py` passe
- [ ] un test neuf échoue si `vibe` réapparaît dans le code, l'outillage ou les consignes, avec la même liste d'exclusions que le premier critère
- [ ] `uv run uvicorn tessera.main:app --host 127.0.0.1 --port 8000 --env-file ../.env` démarre, et `GET /health` renvoie 200 avec `{"status":"ok"}`
- [ ] `GET /api/v1/projects` renvoie 200 et liste au moins `ide-core`
- [ ] `tauri.conf.json` porte `"productName": "Tessera"` et `"identifier": "com.tessera.app"`
- [ ] le rapport final liste les trois renommages manuels du lot 2 et la procédure GitHub du lot 6

## Ce que ça ne fait pas

- **Aucune publication sur PyPI, npm ou crates.io** — le dépôt reste privé, et
  les trois noms y sont de toute façon occupés
- **Aucun choix de licence** — « public mais sans exploitation possible » relève
  d'un ticket distinct, et ce choix a des conséquences qui n'ont rien à voir
  avec un renommage
- **Aucun renommage de fichier sur la machine** — la base, le workspace et le
  dossier des artefacts détachés sont des données de l'utilisateur : le ticket
  dit quoi déplacer, il ne le déplace pas
- **Aucune réécriture de l'historique git** — les anciens commits gardent leurs
  messages ; le nom porté par un commit passé n'est pas une erreur à corriger
- **Aucun changement de comportement** — si un test doit être adapté autrement
  qu'en changeant un import ou une chaîne de caractères, c'est le signe d'une
  régression

## Dépendances

Aucune.

## Estimation

2 jours. Le lot 1 est mécanique mais large — 351 fichiers. Les lots 2 et 6 sont
les seuls à porter un risque réel.

## Risques

- **Perte d'état silencieuse** — renommer `ide_db_path` sans déplacer
  `vibe_ide.db` redémarre sur une base vide : l'historique des coûts et la
  mémoire des agents deviennent invisibles sans qu'aucune erreur ne soit levée.
  Même piège pour le workspace, et pour `vibe-ide-detaches/` qui contient des
  artefacts de projets clients détachés.
- **Changement d'identité de l'app Tauri** — modifier `identifier` fait pointer
  l'app packagée vers un nouveau dossier de données. Acceptable ici, à condition
  de le savoir avant et non après.
- **`.env` est gitignoré** — il porte le nom et il contient des secrets : il se
  met à jour à la main, aucun agent ne le lit ni ne l'écrit.
- **Identité git des commits produits** — `git_link.py` configure l'auteur des
  commits que le pipeline écrit dans les dépôts des projets. Après ce ticket,
  les commits passés restent signés `vibe-ide` et les suivants `tessera` : une
  discontinuité visible dans `git log`, assumée.
- **Skills et slash commands** — un skill renommé n'est visible qu'au démarrage
  de la session suivante. `/run-vibe-ide` cessera de répondre avant que
  `/run-tessera` n'apparaisse.
