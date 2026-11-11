"""The supervisor decides a delegated lesson or rule — ticket-856, ADR-080, ADR-055, ADR-074.

A block under `## Proposées` of `memory/lecons.md` or `memory/contraintes.md` is
accepted (moved whole to its section) or dismissed (dropped, with its reason in
the journal) only when the project delegated that kind in `pipeline.superviseur`.
The guards run in this order, and the model only comes after them:

1. no delegation declared for the kind: nothing is written and the model is not
   called; a block that is sensitive still goes to « À toi » (step 2 costs nothing);
2. the block, or an ADR it cites, is sensitive (`est_sensible`): « À toi », no model;
3. the model, without tools, answers `agir` (accept or dismiss), `a_toi` or `rien`.
   It can escalate, never loosen what step 2 flagged.

The text of a block is never rewritten, and `decisions.md` is never touched. At
most `PLAFOND_DECISIONS` blocks reach the model per sweep; the rest waits.
"""
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from tessera.services.gardes.lecons import PLAFOND_LECONS, lire_lecons
from tessera.services.projets.adr import decouper
from tessera.services.projets.superviseur_declaration import load_config_superviseur
from tessera.services.providers.base import LLMProvider
from tessera.services.supervision.intervention import Resultat
from tessera.services.supervision.superviseur_actions import _LISTE_ADR, RAISON_MAX, SCHEMA_DECISION, Action, Decision, est_sensible, lire_decision
from tessera.services.supervision.superviseur_decision_blocs import TITRE_EN_VIGUEUR, BlocPropose, Genre, blocs_proposes, sections_nommees
from tessera.services.supervision.superviseur_decision_dossier import construire_dossier
from tessera.services.supervision.superviseur_decision_ecriture import FICHIERS, Issue, RefusDecision, appliquer_decision, resume_de
from tessera.services.supervision.superviseur_tri import Intervenir
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

PLAFOND_DECISIONS = 5
_MAX_TOKENS = 600
#: Genre d'un bloc -> clé de `pipeline.superviseur.delegation`.
_DELEGATION: dict[Genre, str] = {"lecon": "lecons", "regle": "regles"}

SCHEMA_DECISION_BLOC: dict[str, Any] = {
    "type": "object",
    "properties": {
        **SCHEMA_DECISION["properties"],
        "issue": {"type": "string", "enum": ["accepter", "ecarter"]},
        "section": {"type": "string"},
    },
    "required": SCHEMA_DECISION["required"],
}


@dataclass
class Passe:
    """What one sweep has spent: the blocks that reached the model, and whether the project turned out held."""

    consultes: int = 0
    abandonne: bool = False

    def permet(self) -> bool:
        return not self.abandonne and self.consultes < PLAFOND_DECISIONS


@dataclass(frozen=True)
class ResultatDecision:
    """The decision on one proposed block, and the intervention when something was written."""

    decision: Decision
    bloc: BlocPropose
    issue: Issue | None = None
    intervention: Resultat | None = None


def _lire(chemin: Path) -> str:
    """The text of a file, empty when absent or unreadable: the guards then have nothing to accept."""
    try:
        return chemin.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _adrs(memoire: Path) -> dict[int, str]:
    return {int(b.numero.removeprefix("ADR-")): b.texte for b in decouper(_lire(memoire / "decisions.md"))}


def _cites(texte: str) -> list[int]:
    numeros = (int(n) for liste in _LISTE_ADR.findall(texte) for n in re.findall(r"\d+", liste))
    return list(dict.fromkeys(numeros))


def raison_sensible(bloc: BlocPropose, adrs: Mapping[int, str]) -> str | None:
    """Why a block is not the supervisor's to decide, or `None`: it, or an ADR it cites, is sensitive."""
    if est_sensible(bloc.texte):
        return "le bloc touche une porte, un mot sensible ou le superviseur"
    for numero in _cites(bloc.texte):
        texte = adrs.get(numero)
        if texte is None:
            return f"ADR-{numero:03d} cité, mais introuvable : non jugé"
        if est_sensible(texte):
            return f"ADR-{numero:03d} cité touche une porte ou un mot sensible"
    return None


def _decision(bloc: BlocPropose, verdict: Literal["a_toi", "rien"], raison: str) -> Decision:
    return Decision(Action.DECIDER, bloc.cible, verdict, " ".join(raison.split())[:RAISON_MAX])


def _issue(sortie: Mapping[str, object]) -> Issue | None:
    if sortie.get("issue") == "accepter":
        return "accepter"
    return "ecarter" if sortie.get("issue") == "ecarter" else None


class SuperviseurDecision:
    """Decides the proposed lessons and rules of a project, one intervention per block."""

    def __init__(self, fournisseur: LLMProvider, intervenir: Intervenir, *, modele: str, systeme: str) -> None:
        self._fournisseur = fournisseur
        self._intervenir = intervenir
        self._modele = modele
        self._systeme = systeme

    async def decider(self, project_id: str, project_path: Path) -> list[ResultatDecision]:
        """Sweep the proposed blocks; sensitive ones go to « À toi », the rest to the model, at most 5."""
        delegation = load_config_superviseur(project_path).delegation
        memoire = project_path / "memory"
        adrs = _adrs(memoire)
        resultats: list[ResultatDecision] = []
        consultes = 0
        for bloc in self._blocs(memoire):
            raison = raison_sensible(bloc, adrs)
            if raison is not None:
                resultats.append(ResultatDecision(_decision(bloc, "a_toi", raison), bloc))
            elif _DELEGATION[bloc.genre] in delegation and consultes < PLAFOND_DECISIONS:
                consultes += 1
                resultat = await self.decider_un(bloc, memoire, adrs)
                resultats.append(resultat)
                if resultat.intervention is not None and resultat.intervention.statut == "abandonne":
                    break  # le projet reste tenu : les suivants attendraient aussi pour rien
        _logger.info("superviseur_decision_balayage", extra={"project": project_id, "blocs": len(resultats)})
        return resultats

    async def decider_bloc(
        self, project_id: str, project_path: Path, cible: str, passe: Passe | None = None
    ) -> list[ResultatDecision]:
        """Decide the one block named `cible`, with the same guards as the sweep; `[]` if gone or not delegated.

        `passe` is shared by the blocks of one sweep: once it holds `PLAFOND_DECISIONS` model calls, or the
        project is held, the model is not called and the block waits for the next sweep.
        """
        delegation = load_config_superviseur(project_path).delegation
        memoire = project_path / "memory"
        adrs = _adrs(memoire)
        for bloc in self._blocs(memoire):
            if bloc.cible != cible:
                continue
            raison = raison_sensible(bloc, adrs)
            if raison is not None:
                return [ResultatDecision(_decision(bloc, "a_toi", raison), bloc)]
            if _DELEGATION[bloc.genre] not in delegation or (passe is not None and not passe.permet()):
                break
            if passe is not None:
                passe.consultes += 1
            resultat = await self.decider_un(bloc, memoire, adrs)
            if passe is not None and resultat.intervention is not None and resultat.intervention.statut == "abandonne":
                passe.abandonne = True
            return [resultat]
        _logger.info("superviseur_decision_bloc", extra={"project": project_id, "cible": cible})
        return []

    @staticmethod
    def _blocs(memoire: Path) -> list[BlocPropose]:
        genres: tuple[Genre, ...] = ("lecon", "regle")
        return [b for g in genres for b in blocs_proposes(_lire(memoire / FICHIERS[g]), g)]

    async def decider_un(self, bloc: BlocPropose, memoire: Path, adrs: Mapping[int, str]) -> ResultatDecision:
        """Ask the model about one block the guards let through, check its answer, write it; never raises."""
        dossier = construire_dossier(bloc, [adrs[n] for n in _cites(bloc.texte) if n in adrs], _voisine(bloc, memoire))
        sortie = await self._demander(dossier)
        if sortie is None:
            return ResultatDecision(_decision(bloc, "rien", "sortie du modèle absente : rien n'est écrit"), bloc)
        try:
            decision = lire_decision(sortie)
        except ValueError as exc:
            return ResultatDecision(_decision(bloc, "rien", str(exc)), bloc)
        if decision.action is not Action.DECIDER or decision.cible != bloc.cible:
            return ResultatDecision(_decision(bloc, "rien", "action ou cible hors du bloc à décider"), bloc)
        if decision.verdict != "agir":
            return ResultatDecision(decision, bloc)
        return await self._ecrire(bloc, decision, sortie, memoire)

    async def _ecrire(
        self, bloc: BlocPropose, decision: Decision, sortie: Mapping[str, object], memoire: Path
    ) -> ResultatDecision:
        issue = _issue(sortie)
        if issue is None:
            return ResultatDecision(_decision(bloc, "rien", "issue absente ou hors énumération"), bloc)
        try:
            vers = _accueil(bloc, issue, sortie, memoire)
        except RefusDecision as exc:
            return ResultatDecision(_decision(bloc, "a_toi", f"décision refusée : {exc}"), bloc)
        ecriture = appliquer_decision(bloc, issue, vers, resume_de(issue, vers, decision.raison))
        return ResultatDecision(decision, bloc, issue, await self._intervenir(Action.DECIDER, ecriture))

    async def _demander(self, dossier: str) -> Mapping[str, object] | None:
        try:
            reponse = await self._fournisseur.complete(
                system=self._systeme, user=dossier, model=self._modele,
                max_tokens=_MAX_TOKENS, schema=SCHEMA_DECISION_BLOC,
            )
        except Exception as exc:  # noqa: BLE001 — un modèle indisponible n'écrit rien
            _logger.warning("superviseur_decision_modele_indisponible", extra={"erreur": str(exc)[:200]})
            return None
        return reponse.structured


def _voisine(bloc: BlocPropose, memoire: Path) -> str:
    """The neighbouring section: the lessons in force, or the sections a rule can join."""
    if bloc.genre == "lecon":
        return "\n".join(f"- {lecon}" for lecon in lire_lecons(memoire).en_vigueur)
    return "\n".join(f"- {titre}" for titre in sections_nommees(_lire(memoire / FICHIERS["regle"])))


def _accueil(bloc: BlocPropose, issue: Issue, sortie: Mapping[str, object], memoire: Path) -> str:
    """The section an accepted block joins (`""` for a dismissal); `RefusDecision` when it cannot join."""
    if issue == "ecarter":
        return ""
    if bloc.genre == "lecon":
        if len(lire_lecons(memoire).en_vigueur) >= PLAFOND_LECONS:
            raise RefusDecision(f"{PLAFOND_LECONS} leçons déjà en vigueur : un humain compacte")
        return TITRE_EN_VIGUEUR
    demandee = sortie.get("section")
    titres = {t.casefold(): t for t in sections_nommees(_lire(memoire / FICHIERS["regle"]))}
    if not isinstance(demandee, str) or demandee.strip().casefold() not in titres:
        raise RefusDecision("section d'accueil absente ou inconnue")
    return titres[demandee.strip().casefold()]
