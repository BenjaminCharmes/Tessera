---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 1
id: ticket-948
pr_number: null
preuve_reelle: true
priority: high
status: done
title: A project venv whose launcher Smart App Control blocks is repaired before its
  tests and services
type: fix
---

# ticket-948 — Le venv d'un projet dont Smart App Control bloque le lanceur est réparé avant ses tests et ses services

## Objectif

Qu'un `.venv` créé par uv dont le lanceur `python.exe` est refusé par Smart
App Control ne fasse plus échouer le testeur d'une file ni le démarrage d'un
service : Tessera le répare, le journalise, puis continue. **Sans qu'un agent
puisse se servir de cette réparation pour faire écrire le backend ailleurs
que dans son propre venv, ni lui faire copier d'autres fichiers que ceux d'un
interpréteur uv.**

## Contexte

Smart App Control juge chaque fichier selon sa réputation, et rejuge parfois
un fichier qui passait. Le lanceur `python.exe` que uv copie dans
`.venv/Scripts` est refusé par moments (Code Integrity 3033/3077/3118,
« os error 4551 », « Une stratégie de contrôle d'application a bloqué ce
fichier »). Constaté le 05/11 (backend de Tessera), puis le 12/11 vers
10:45 UTC pour vigie, carriere et freelance, alors que curio, affut,
habit-tracker et repo-health, au binaire identique, passaient. Un
`uv venv --clear` ne suffit pas : le lanceur neuf est rebloqué.

La parade éprouvée (05/11 et 12/11) : copier `python.exe`, `pythonw.exe`,
`python3*.dll` et `vcruntime140*.dll` de l'interpréteur de base, qui reste
autorisé, dans `.venv/Scripts`, en gardant l'original en `*.lanceur-uv`.
Python retrouve son venv par `pyvenv.cfg`, et `uv run` remarche.

**Premier run (13/11, run c4b4e611) bloqué par l'audit sécurité, à juste
titre.** La réparation tourne dans le backend, sous le compte utilisateur,
alors que tout ce qu'elle lisait vient du dossier que l'agent écrit :
- la source était la clé `home` de `pyvenv.cfg`, que l'agent peut réécrire, et
  le seul contrôle cherchait les mots `uv` et `python` dans le chemin
  (`C:\x\uv\python` passait) : l'agent choisissait les DLL copiées ;
- la destination `.venv/Scripts` n'était pas résolue : une jonction
  l'envoyait hors du worktree, et l'isolation par compte agent (ADR-083,
  ADR-085) ne protégeait plus rien.

## Solution proposée

1. Un module `services/verification/venv_sac.py` : `reparer_venv(venv,
   racine_ecriture)` applique la parade.
2. **Source.** La racine des interpréteurs uv se lit **côté backend**, jamais
   dans un fichier du projet : `UV_PYTHON_INSTALL_DIR` s'il est défini, sinon
   la sortie de `uv python dir`, résolue une fois et mise en cache. `home`
   (lu dans `pyvenv.cfg`) n'est accepté que si, **résolu**
   (`Path.resolve(strict=True)`), il est sous cette racine résolue
   (`is_relative_to`). Sinon : `VenvIrreparable`, rien n'est copié.
3. **Destination.** `.venv` et `.venv/Scripts`, résolus, doivent être sous
   la racine d'écriture du run, résolue. Ni `.venv`, ni `.venv/Scripts`, ni un
   fichier cible déjà présent ne doivent être un lien (symlink ou jonction :
   `is_symlink()`, et sous Windows l'attribut `FILE_ATTRIBUTE_REPARSE_POINT`
   de `os.lstat`). Sinon : `VenvIrreparable`, rien n'est copié.
4. **Fichiers.** Seuls les noms de la liste fixe ci-dessus sont copiés, et
   chaque source doit être un fichier ordinaire (pas un lien). Idempotent : un
   lanceur déjà remplacé ne bouge pas, un `*.lanceur-uv` existant n'est jamais
   écrasé.
5. Le testeur et le démarrage d'un service reconnaissent l'échec 4551 sur un
   `python.exe` de `.venv`, appellent `reparer_venv`, journalisent
   `venv_repare` (projet, dossier), puis relancent la commande **une seule
   fois**. Un second échec reste une panne d'environnement (ADR-037).
6. Hors Windows, rien ne change.

## Preuve réelle

Dans un dossier jetable : `uv venv`, puis remplacer `python.exe` du venv par
un fichier que Smart App Control refuse (ou attendre un refus 4551 réel) ;
lancer `reparer_venv` sur ce `.venv` : le lanceur original est gardé en
`python.exe.lanceur-uv`, `.venv\Scripts\python.exe -c "import sys"` rend 0,
et un second appel ne change rien. Puis : `.venv\Scripts` remplacé par une
jonction vers un autre dossier → refus, rien d'écrit dans ce dossier. Enfin
un run réel d'un projet dont le venv a été bloqué : le journal porte
`venv_repare` et la commande repart une fois.

## Critères d'acceptation

- [ ] Un test (`tmp_path`, fausse racine uv par `UV_PYTHON_INSTALL_DIR`) :
      `reparer_venv` copie les fichiers attendus, garde l'original en
      `python.exe.lanceur-uv`, et un second appel ne change rien.
- [ ] Un test : un `pyvenv.cfg` sans `home` est refusé sans rien copier.
- [ ] Un test : un `home` hors de la racine uv est refusé sans rien copier,
      **même si son chemin contient `uv` et `python`** (par exemple
      `<tmp>/ailleurs/uv/python/cpython-3.11`).
- [ ] Un test : un `home` qui est un lien vers un dossier hors de la racine uv
      est refusé (le contrôle porte sur le chemin résolu).
- [ ] Un test : `.venv/Scripts` qui est un lien vers un dossier hors de la
      racine d'écriture est refusé, et ce dossier reste inchangé.
- [ ] Un test : un `.venv` situé hors de la racine d'écriture est refusé.
- [ ] Un test, avec un lanceur double qui échoue une fois en 4551 puis
      réussit : le testeur répare, journalise `venv_repare` et relance une
      seule fois.
- [ ] Un test : un double qui échoue deux fois rend une panne
      d'environnement, sans troisième essai.
- [ ] Un test : sur une plateforme autre que Windows, `reparer_venv` n'est
      jamais appelé.
- [ ] `backend/tests/test_longueur_des_fichiers.py` n'est pas modifié : un
      fichier qui dépasse son plafond se découpe.

Les tests qui créent un lien se sautent (`pytest.skip`) là où le système
refuse d'en créer, et seulement là.

## Ce que ça ne fait pas

- Ne contourne pas Smart App Control : l'interpréteur copié est celui de
  base, déjà autorisé ; aucun fichier refusé n'est exécuté autrement.
- Ne répare pas les DLL d'extensions (pydantic-core, rpds-py, mypy) :
  celles-ci s'épinglent par projet (tickets 385 et 939).
- Ne fait pas confiance à la sortie des tests : elle peut déclencher une
  réparation, mais une réparation ne peut plus rien écrire hors du venv du
  run ni copier autre chose qu'un interpréteur uv.