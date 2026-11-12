---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.5
id: ticket-952
pr_number: null
priority: high
status: todo
title: "The description guard covers projects hosted inside the Tessera folder"
type: fix
---

# ticket-952 — La garde de la description couvre les projets rangés dans le dossier de Tessera

## Objectif

Que la description écrite par le lot de documentation pour un projet hébergé
ne puisse plus être celle de Tessera, dans la disposition réelle des dossiers.

## Contexte

Le ticket-936 répond à l'incident du 11/11 (homelab-monitor, ticket-018) :
« Tessera est un IDE multi-projets avec orchestration d'agents IA,
auto-hébergé. Le tableau de bord… ». Sa garde, `phrases_interdites`
(`services/documentation/documentation_ailleurs.py`), ne l'aurait pas
arrêté. Vérifié le 12/11 sur la machine :

1. Elle n'ajoute la première phrase du `CLAUDE.md` racine que si le projet
   n'est **pas sous** la racine de Tessera
   (`racine not in projet.parents`). Or tous les projets hébergés vivent dans
   `<tessera>/projects/<nom>` : pour homelab-monitor, la phrase n'est jamais
   dans la liste. L'exception voulue ne concerne que `ide-core`.
2. La comparaison est une égalité de première phrase. Celle du `CLAUDE.md`
   réel est « Tu travailles sur **Tessera** : un IDE multi-projets… », pas
   « Tessera est un IDE multi-projets… » : même avec la liste correcte, le
   texte de l'incident passe.

Les tests du 936 ne le voyaient pas : `_monde` place l'espace de travail
**hors** de la racine, et y écrit une phrase identique à celle refusée.

## Solution proposée

1. Le projet exempté se reconnaît par son nom ou son dossier
   (`<racine>/projects/ide-core`), plus par sa position sous la racine.
2. Pour un autre projet, une description dont la première phrase a
   « Tessera » pour sujet (elle commence par « Tessera », hors casse et
   ponctuation) est refusée, comme une phrase reprise ailleurs. Citer
   Tessera plus loin reste permis.
3. Les tests reproduisent la disposition réelle : espace de travail =
   `<racine>/projects`, `CLAUDE.md` racine avec la phrase réelle d'ouverture.

## Critères d'acceptation

- [ ] Un test, espace de travail sous la racine : la description exacte de
      l'incident du 11/11 est refusée pour `projects/homelab-monitor`.
- [ ] Un test : la même description est acceptée pour `projects/ide-core`.
- [ ] Un test : « Sert à mesurer l'orchestration de Tessera. » reste acceptée
      pour un projet hébergé.
- [ ] Un test : la description d'un projet voisin reste refusée quand
      l'espace de travail est sous la racine.
- [ ] Les tests existants de `test_documentation_ailleurs.py` passent.

## Ce que ça ne fait pas

- Ne cherche pas pourquoi l'agent de documentation a écrit cette phrase :
  le ticket-414 lui tient déjà les consignes ancêtres à l'écart. Ceci ferme
  la porte, pas la source.
- Ne corrige pas une description déjà écrite.
