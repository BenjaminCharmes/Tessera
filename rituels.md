---
rituels:
  - id: lecture-veille
    titre: Lecture de la veille
    rythme: { type: hebdo, jour: lundi, heure: "09:00" }
    duree_min: 15
    phrase: ouvrir Vigie
    detail: Lire le résumé de la semaine écoulée.
    projets: [vigie]

  - id: point-revenus
    titre: Point revenus
    rythme: { type: hebdo, jour: lundi, heure: "18:30" }
    duree_min: 30
    phrase: point revenus
    detail: Chiffres de la semaine (visiteurs, Search Console), page « À toi de jouer », une décision.
    projets: [kadoomi, devinoo]

  - id: point-hebdo-travail
    titre: Point hebdo travail
    rythme: { type: hebdo, jour: vendredi, heure: "16:00" }
    duree_min: 10
    phrase: point hebdo
    detail: Noter la semaine de travail.
    projets: [carriere]

  - id: releve-marche
    titre: Relevé marché
    rythme: { type: mensuel, jour: 5, heure: "09:00" }
    duree_min: 20
    phrase: relevé marché
    detail: Nouvelles offres reportées dans Carrière, offres disparues clôturées.
    projets: [carriere]

  - id: rapport-mensuel
    titre: Rapport mensuel
    rythme: { type: mensuel, jour: 18, heure: "10:00", avant: 22 }
    duree_min: 20
    phrase: point mensuel
    detail: Rédiger le rapport du mois, à rendre avant le 22.
    projets: [carriere]

  - id: passe-black-friday-2026
    titre: Passe Black Friday
    rythme: { type: unique, du: "2026-11-23", au: "2026-11-27" }
    duree_min: 45
    phrase: passe Black Friday
    detail: Revoir tous les achats suivis et comparer avec les prix du moment.
    projets: [affut]
---

# Rituels

Les actions qui reviennent et qu'on oublie quand la notification est fermée.
Ce fichier est versionné : la liste est la même sur chaque PC, quel que soit le
compte Claude utilisé. Tessera la lit et affiche un bandeau sur toutes ses vues
tant qu'un rituel en retard n'est ni fait ni reporté.

## Écrire un rituel

| Champ | Sens |
|---|---|
| `id` | identifiant stable, en kebab-case : l'état « fait » s'y rattache |
| `titre` | ce que montre Tessera |
| `rythme` | `hebdo` (`jour` : lundi…dimanche, `heure`), `mensuel` (`jour` : 1-28, `heure`, `avant` facultatif : jour limite), `unique` (`du`, `au` : dates) |
| `duree_min` | durée indicative, en minutes |
| `phrase` | ce qu'on dit à Claude pour le lancer |
| `detail` | une phrase sur ce qu'il faut faire |
| `projets` | ids des projets Tessera concernés : un bouton ouvre chacun |

Les heures sont celles du PC. Ce qui est propre à un employeur ou à un client ne
s'écrit pas ici : un libellé générique, et le détail dans un skill personnel.

L'état « fait » ou « reporté » reste dans la base locale de chaque PC : un
rituel fait sur un poste peut encore apparaître sur un autre, un clic suffit.
