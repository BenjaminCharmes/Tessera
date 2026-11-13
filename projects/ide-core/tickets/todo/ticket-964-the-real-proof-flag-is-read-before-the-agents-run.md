---
agent: codeur
created: 2026-11-13
depends_on: []
estimated_days: 0.5
id: ticket-964
pr_number: null
priority: high
status: todo
title: "The real-proof flag of a ticket is read before any agent runs, not after"
type: fix
---

# ticket-964 — Le drapeau `preuve_reelle` d'un ticket se lit avant tout agent, pas après

## Objectif

Qu'un agent ne puisse pas lever la retenue d'une PR qui attend une preuve
réelle en réécrivant le ticket pendant son run.

## Contexte

Audit du lot 941-961 (13/11). `services/pipeline/pipeline_livraison.py`
(lignes 35-37) relit le ticket **après** le run, par `orch._ticket_svc`,
dans le dossier où le codeur vient d'écrire, pour décider de
`retenir_pour_preuve`. Un codeur qui retire `preuve_reelle: true` du
frontmatter de son ticket rend sa PR au merge automatique, sans preuve.
`reprise_surveillance.py` relit de même le ticket au redémarrage.

## Solution proposée

1. Au début du run, avant le premier agent, lire `preuve_reelle` du ticket
   et le garder sur le run (`PipelineRun`), comme la racine d'écriture est
   figée (ticket-119).
2. `pipeline_livraison` décide `retenir_pour_preuve` sur cette valeur figée,
   plus sur une relecture du ticket.
3. Une PR retenue pour preuve porte le label ou la trace que
   `reprise_surveillance` lit au redémarrage, plutôt que le fichier du ticket
   dans le dossier du run : si ce n'est pas possible simplement, la reprise
   lit le ticket **sur la base** (`origin/<base>`), jamais dans le dossier du
   run.

## Critères d'acceptation

- [ ] Un test : un run dont le ticket porte `preuve_reelle: true` au départ,
      et dont le codeur (simulé) réécrit le ticket sans ce drapeau, ouvre sa
      PR sans la confier au merge.
- [ ] Un test : un ticket sans `preuve_reelle` au départ, que le codeur
      réécrit avec `preuve_reelle: true`, garde son comportement habituel.
- [ ] Un test : au redémarrage, une PR ouverte dont le ticket portait
      `preuve_reelle: true` sur la base n'est pas reprise par la surveillance,
      même si le fichier du dossier du run a perdu le drapeau.

## Ce que ça ne fait pas

- Ne protège pas tout le dossier `tickets/` en écriture : un agent de design
  y écrit légitimement.
