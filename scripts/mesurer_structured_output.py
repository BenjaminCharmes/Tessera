"""Measures ``output_format`` on the pinned Agent SDK (ticket-611).

Usage, from ``backend/``::

    python ../scripts/mesurer_structured_output.py <mesure>

where ``<mesure>`` is one of ``outils``, ``tours``, ``relances``, ``schema``,
``ligne``, ``on_tool_use``. Each one prints a JSON line with what it observed.
Real calls, on haiku (``MESURE_MODELE`` overrides), read-only tools: a few cents each. Nothing here touches
``backend/src/``; ``_build_options`` is imported and given ``output_format``
after the fact, exactly as ticket-612 will.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import claude_agent_sdk as sdk_module
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    ToolUseBlock,
    query,
)
from claude_agent_sdk._cli_version import __cli_version__
from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from jsonschema import Draft7Validator

from tessera.services.providers import agent_sdk
from tessera.services.providers.agent_sdk import _build_options

RACINE = Path(__file__).resolve().parents[1]
CWD = RACINE / "backend"
MODELE = os.environ.get("MESURE_MODELE", "claude-haiku-4-5")
OUTILS = ["Read", "Glob", "Grep"]  # OUTILS_DE_RELECTURE (agent_runner.py)
PROMPT_REVIEWER = (RACINE / "agents" / "prompts" / "reviewer.md").read_text("utf-8")
DEMANDE = (
    "Review src/tessera/services/providers/noms.py and "
    "src/tessera/services/providers/base.py: read both files, then conclude."
)

# Le schéma du ticket-614, sans `minimum`/`maximum`.
SCHEMA_REVIEWER: dict[str, Any] = {
    "type": "object",
    "required": ["verdict", "summary", "blocking"],
    "properties": {
        "verdict": {"enum": ["APPROVED", "CHANGES_REQUESTED"]},
        "summary": {"type": "string"},
        "blocking": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["text", "confidence"],
                "properties": {
                    "text": {"type": "string"},
                    "location": {"type": "string"},
                    "confidence": {"type": "integer"},
                },
            },
        },
        "suggestions": {"type": "array", "items": {"type": "string"}},
    },
}


def options(schema: dict[str, Any] | None, tours: int = 10, systeme: str = PROMPT_REVIEWER):
    """The options ``_build_options`` gives, plus ``output_format`` when asked."""
    opts = _build_options(
        system=systeme, model=MODELE, max_turns=tours, max_budget_usd=0.5,
        cwd=CWD, allowed_tools=OUTILS,
    )
    if schema is not None:
        opts.output_format = {"type": "json_schema", "schema": schema}
    return opts


async def jouer(opts: Any, demande: str = DEMANDE) -> dict[str, Any]:
    """Runs one call and reports tools, turns and result of the whole stream."""
    out: dict[str, Any] = {"outils_dispos": None, "blocs": [], "assistant": 0, "structured": None}
    try:
        await _lire(out, query(prompt=demande, options=opts))
    except Exception as exc:  # noqa: BLE001 — l'échec du SDK est lui-même la mesure
        out["exception"] = f"{type(exc).__name__}: {exc}"
    return out


async def _lire(out: dict[str, Any], flux: Any) -> None:
    async for msg in flux:
        if isinstance(msg, SystemMessage) and msg.subtype == "init":
            out["outils_dispos"] = msg.data.get("tools")
        elif isinstance(msg, AssistantMessage):
            out["assistant"] += 1
            noms = [b.name for b in msg.content if isinstance(b, ToolUseBlock)]
            if noms:
                out["blocs"].append(noms)
        elif isinstance(msg, ResultMessage):
            out.update(
                subtype=msg.subtype, num_turns=msg.num_turns, is_error=msg.is_error,
                structured=msg.structured_output, cout=msg.total_cost_usd,
                erreurs=msg.errors,
            )


def conforme(valeur: Any) -> list[str]:
    """Validation errors of ``valeur`` against the reviewer schema."""
    return [e.message for e in Draft7Validator(SCHEMA_REVIEWER).iter_errors(valeur)]


async def mesure_outils() -> dict[str, Any]:
    return await jouer(options(SCHEMA_REVIEWER))


async def mesure_tours() -> dict[str, Any]:
    # Le même appel sous trois plafonds : où `max_turns` coupe-t-il ?
    sortie: dict[str, Any] = {}
    for tours in (3, 2, 1):
        for essai in (1, 2):
            rendu = await jouer(options(SCHEMA_REVIEWER, tours=tours))
            rendu["erreurs_schema"] = conforme(rendu["structured"]) if rendu["structured"] else None
            sortie[f"max_turns_{tours}_essai_{essai}"] = rendu
    return sortie


async def mesure_sequentiel() -> dict[str, Any]:
    # Trois lectures l'une après l'autre : de quoi dépasser un plafond serré.
    demande = (
        "Read, one file per step and never in parallel, noms.py, base.py and "
        "__init__.py under src/tessera/services/providers, then conclude."
    )
    return {f"max_turns_{t}": await jouer(options(SCHEMA_REVIEWER, tours=t), demande) for t in (2, 10)}


async def mesure_relances() -> dict[str, Any]:
    # Un premier appel d'outil qui échoue à la validation, puis la correction :
    # les relances comptent-elles dans `max_turns` ?
    schema = {"type": "object", "required": ["code"],
              "properties": {"code": {"type": "string", "pattern": "^ZX[0-9]{6}$"}}}
    demande = (
        "Call the StructuredOutput tool with code set to 'abc' as a first attempt. "
        "If it is rejected, call it again with a value that satisfies the schema."
    )
    sortie = {f"tours_{t}": await jouer(options(schema, tours=t), demande) for t in (1, 2, 10)}
    # Un schéma qu'aucune valeur ne satisfait : la borne de relances du SDK.
    impossible = {"type": "object", "required": ["x"], "properties": {"x": {"allOf": [
        {"type": "string", "maxLength": 1}, {"type": "string", "minLength": 2}]}}}
    sortie["impossible"] = await jouer(options(impossible, tours=30), "Answer with x = 'a'.")
    return sortie


async def mesure_schema() -> dict[str, Any]:
    invalide = {"type": "object", "properties": {"a": {"type": "pas-un-type"}}}
    rendu = await jouer(options(invalide, tours=3), "Answer with a = 1.")
    exe = Path(sdk_module.__file__).parent / "_bundled" / "claude.exe"
    version = subprocess.run([str(exe), "--version"], capture_output=True, text=True)
    return {
        "cli_declare": __cli_version__, "cli_reel": version.stdout.strip(),
        "schema_invalide": rendu,
    }


def mesure_ligne() -> dict[str, Any]:
    out: dict[str, Any] = {"schema_chars": len(json.dumps(SCHEMA_REVIEWER))}
    for nom, systeme in {"reviewer.md": PROMPT_REVIEWER, "pire_cas_24000": "x" * 24_000}.items():
        out[nom] = {
            "avec_schema": _longueur(options(SCHEMA_REVIEWER, systeme=systeme)),
            "sans_schema": _longueur(options(None, systeme=systeme)),
        }
    return out


def _longueur(opts: Any) -> int:
    """Characters of the command line the SDK would spawn, as Windows quotes it."""
    transport = SubprocessCLITransport(prompt="x", options=opts)
    # Le chemin n'est résolu qu'à connect() : on le fixe sans lancer le CLI.
    transport._cli_path = str(Path(sdk_module.__file__).parent / "_bundled" / "claude.exe")
    return len(subprocess.list2cmdline(transport._build_command()))


async def mesure_on_tool_use() -> dict[str, Any]:
    vus: list[str] = []

    async def capter(nom: str, _entree: dict[str, Any]) -> None:
        vus.append(nom)

    original = agent_sdk._build_options
    agent_sdk._build_options = lambda **kw: _avec_schema(original(**kw))  # type: ignore[assignment]
    try:
        prov = agent_sdk.ClaudeAgentSDKProvider(max_turns=10, allowed_tools=OUTILS)
        await prov.stream(system=PROMPT_REVIEWER, user=DEMANDE, model=MODELE,
                          max_tokens=4096, cwd=CWD, on_tool_use=capter)
    finally:
        agent_sdk._build_options = original  # type: ignore[assignment]
    return {"on_tool_use": vus}


def _avec_schema(opts: Any) -> Any:
    opts.output_format = {"type": "json_schema", "schema": SCHEMA_REVIEWER}
    return opts


MESURES = {
    "outils": mesure_outils, "tours": mesure_tours, "relances": mesure_relances,
    "schema": mesure_schema, "sequentiel": mesure_sequentiel, "on_tool_use": mesure_on_tool_use,
}


def main() -> None:
    nom = sys.argv[1]
    if nom == "ligne":
        print(json.dumps(mesure_ligne(), default=str))
        return
    print(json.dumps(asyncio.run(MESURES[nom]()), default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
