---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 1
id: ticket-948
pr_number: null
priority: high
status: todo
title: "A project venv whose launcher Smart App Control blocks is repaired before its tests and services"
type: fix
---

# ticket-948 — Le venv d'un projet dont Smart App Control bloque le lanceur est réparé avant ses tests et ses services

## Objectif

Qu'un `.venv` créé par uv dont le lanceur `python.exe` est refusé par Smart
App Control ne fasse plus échouer le testeur d'une file ni le démarrage d'un
service : Tessera le répare, le journalise, puis continue.

## Contexte

Smart App Control juge chaque fichier selon sa réputation, et rejuge parfois
un fichier qui passait. Le lanceur `python.exe` que uv copie dans
`.venv/Scripts` est refusé par moments (Code Integrity 3033/3077/3118,
« os error 4551 », « Une stratégie de contrôle d'application a bloqué ce
fichier »). Constaté le 05/11 (backend de Tessera), puis le 12/11 vers
10:45 UTC pour vigie, carriere et freelance, alors que curio, affut,
habit-tracker et repo-health, au binaire identique, passaient. Un
`uv venv --clear` ne suffit pas : le lanceur neuf est rebloqué.

La parade éprouvée (mémoire de la session, 05/11 et 12/11) : copier
`python.exe`, `pythonw.exe`, `python3.dll`, `python311.dll` et
`vcruntime140*.dll` de l'interpréteur de base (la clé `home` de
`pyvenv.cfg`), qui reste autorisé, dans `.venv/Scripts`, en gardant
l'original en `*.lanceur-uv`. Python retrouve son venv par `pyvenv.cfg`, et
`uv run` remarche. Un `uv sync` qui recrée le venv remet le lanceur bloqué.

## Solution proposée

1. Un module `services/verification/venv_sac.py` : `reparer_venv(dossier)`
   applique la parade à un `.venv` donné. Il est idempotent : un lanceur déjà
   remplacé ne bouge pas, et un `*.lanceur-uv` existant n'est jamais écrasé.
   Il refuse un `home` absent ou hors des interpréteurs gérés par uv.
2. Le testeur et le démarrage d'un service reconnaissent l'échec de
   lancement Windows 4551 sur un `python.exe` de `.venv`, appellent
   `reparer_venv`, journalisent `venv_repare` (projet, dossier), puis
   relancent la commande **une seule fois**. Un second échec reste une panne
   d'environnement (ADR-037).
3. Hors Windows, rien ne change.

## Critères d'acceptation

- [ ] Un test (`tmp_path`, faux interpréteur de base) : `reparer_venv` copie
      les fichiers attendus, garde l'original en `python.exe.lanceur-uv`, et
      un second appel ne change rien.
- [ ] Un test : un `pyvenv.cfg` sans `home`, ou dont `home` n'est pas un
      interpréteur uv, est refusé sans rien copier.
- [ ] Un test, avec un lanceur double qui échoue une fois en 4551 puis
      réussit : le testeur répare, journalise `venv_repare` et relance une
      seule fois.
- [ ] Un test : un double qui échoue deux fois rend une panne
      d'environnement, sans troisième essai.
- [ ] Un test : sur une plateforme autre que Windows, `reparer_venv` n'est
      jamais appelé.

## Ce que ça ne fait pas

- Ne contourne pas Smart App Control : l'interpréteur copié est celui de
  base, déjà autorisé ; aucun fichier refusé n'est exécuté autrement.
- Ne répare pas les DLL d'extensions (pydantic-core, rpds-py, mypy) :
  celles-ci s'épinglent par projet (tickets 385 et 939).
