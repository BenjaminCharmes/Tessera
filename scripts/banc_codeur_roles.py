"""Real roles of a bench cell: uv sync, coder, tests, reviewer and validator.

Ticket-1055, ADR-095. Imports `provider_pour_role`, `lire_verdict`,
`ValidatorService` and `_extract_criteria` read only; never `Orchestrator`,
`RunLock`, delivery or the database. Not covered by a model call in tests.
"""
from __future__ import annotations

import asyncio
import subprocess
import time
from pathlib import Path

from banc_codeur_bras import Bras
from banc_codeur_cellule import Appel, Controle, IndisponibleErreur, Roles, diff_de_la_copie

from tessera.config import settings
from tessera.services.pipeline.pipeline_text import _extract_criteria
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.par_role import modele_du_role, provider_pour_role
from tessera.services.verdicts.reviewer_schema import REVIEWER_SCHEMA
from tessera.services.verdicts.validator import ValidatorService
from tessera.services.verdicts.verdict_reviewer import lire_verdict

_MAX_TOKENS = 8192
_VERIFIER = "../scripts/verifier.py"


async def _lancer(commande: list[str], cwd: Path) -> bool:
    def _run() -> bool:
        return subprocess.run(commande, cwd=cwd, capture_output=True).returncode == 0

    return await asyncio.to_thread(_run)


def _coeur(dossier: Path, bras: Bras) -> Roles:
    codeur = provider_pour_role(dossier, "codeur")
    reviewer = provider_pour_role(dossier, "reviewer", allow_tools=False)
    juge = provider_pour_role(dossier, "validateur", allow_tools=False)
    prompt = (dossier / "agents" / "prompts" / "codeur.md").read_text(encoding="utf-8")
    modele_rev = modele_du_role(dossier, "reviewer") or ""
    prompt_reviewer = (dossier / "agents" / "prompts" / "reviewer.md").read_text(encoding="utf-8")
    validateur = ValidatorService(
        juge, dossier / "agents" / "prompts", modele_du_role(dossier, "validateur")
    )

    async def coder(cwd: Path, ticket: str, retour: str) -> Appel:
        entree = ticket if not retour else f"{ticket}\n\n## Retour du tour précédent\n{retour}"
        debut = time.monotonic()
        try:
            r = await codeur.complete(system=prompt, user=entree, model=bras.modele,
                                      max_tokens=_MAX_TOKENS, cwd=cwd)
        except ProviderIndisponible as exc:
            raise IndisponibleErreur(str(exc)) from exc
        jetons = (r.input_tokens, r.output_tokens, r.cache_read_tokens)
        return Appel(float(r.cost_usd or 0.0), jetons, round((time.monotonic() - debut) * 1000))

    async def controler(cwd: Path, ticket: str, tests_verts: bool) -> Controle:
        diff = diff_de_la_copie(cwd)
        contexte = f"{ticket}\n\n## Code produit par le codeur\n{diff}"
        rev = await reviewer.complete(system=prompt_reviewer, user=contexte, model=modele_rev,
                                      max_tokens=_MAX_TOKENS, schema=REVIEWER_SCHEMA, cwd=cwd)
        ok_rev, raison = lire_verdict(rev.structured, settings.reviewer_confidence_threshold)
        val = await validateur.validate(
            criteria=_extract_criteria(ticket), code_produced=diff, test_result=None,
            project_root=cwd, ticket_type="feat",
        )
        ok_val = val.verdict == "APPROVED"
        retour = "\n".join(x for x in (raison, "" if ok_val else val.feedback) if x)
        return Controle(ok_rev and ok_val, retour, float(rev.cost_usd or 0.0))

    async def env(cwd: Path) -> bool:
        return await _lancer(["uv", "sync"], cwd / "backend")

    async def tester(cwd: Path) -> bool:
        return await _lancer(
            ["uv", "run", "python", _VERIFIER, "--impact", "base"], cwd / "backend"
        )

    return Roles(env=env, coder=coder, tester=tester, controler=controler)


def roles_reels(dossier: Path, bras: Bras) -> Roles:
    """Roles built from the arm's temporary project folder (`manifeste_temporaire`)."""
    return _coeur(dossier, bras)
