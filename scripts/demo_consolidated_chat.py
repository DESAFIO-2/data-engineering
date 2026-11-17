"""Reproduce the same questions against pre-change CLI and current consolidated chat."""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
from collections.abc import Iterator
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from types import ModuleType
from unittest.mock import patch

from rag import cli, consolidated_chat
from rag.config import ROOT, get_settings
from rag.live import load_snapshot

QUESTIONS = [
    "Oi",
    "O que consta na RENAME sobre metformina?",
    "850 mg",
    "comprimido",
    "Tem estoque UBS em Planaltina?",
    "E na Farmácia Popular?",
    "Posso trocar pela de ação prolongada?",
    "sair",
]
RELEASE = "data/releases/corpus-consolidado-v5-aprovado-2026-11-10"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default="HEAD")
    parser.add_argument("--live-model", action="store_true")
    parser.add_argument("--output", default="docs/demos/demo-chat-v5.md")
    args = parser.parse_args()
    commit = subprocess.check_output(
        ["git", "rev-parse", args.baseline_ref], cwd=ROOT, text=True
    ).strip()
    source = subprocess.check_output(["git", "show", f"{commit}:src/rag/cli.py"], cwd=ROOT).decode(
        "utf-8"
    )
    baseline = ModuleType("rag.baseline_cli")
    exec(compile(source, "baseline_cli.py", "exec"), baseline.__dict__)
    settings = get_settings()
    offline = replace(
        settings,
        google_api_key="",
        google_api_key_fallback_1="",
        google_api_key_fallback_2="",
    )
    snapshot = load_snapshot(ROOT / "data/gold/infosaude_live_snapshot.json")
    reports = []
    for title, module, release in [
        ("Antes: seleção explícita da v5", baseline, RELEASE),
        ("Antes: lote legado", baseline, "data/releases/rag-lote-1-aprovado-2026-11-05"),
        ("Depois: chat consolidado v5", cli, RELEASE),
    ]:
        questions = iter(QUESTIONS)

        def user_input(prompt: str, messages: Iterator[str] = questions) -> str:
            question = next(messages)
            print(prompt + question)
            return question

        def reuse_snapshot(*unused: object) -> object:
            print("Demonstração: reutilizando o snapshot local; sem nova sincronização.")
            return snapshot

        output = io.StringIO()
        effective = settings if args.live_model and module is cli else offline
        with (
            patch.object(module, "get_settings", return_value=effective),
            patch.object(module, "_sync_live", side_effect=reuse_snapshot),
            patch.object(consolidated_chat, "sync_live", side_effect=reuse_snapshot),
            patch("builtins.input", side_effect=user_input),
            patch.object(sys, "argv", ["app.py", "chat", "--release", release]),
            redirect_stdout(output),
            redirect_stderr(output),
        ):
            code = module.main()
        reports.append(f"## {title}\n\nSaída: {code}.\n\n```text\n{output.getvalue()}\n```\n")
    mode = "modelo local configurado na v2" if args.live_model else "sem chave; fallback documental"
    text = (
        "# Demonstração reproduzível do chat v5\n\n"
        f"Baseline: `{commit}`. Depois: árvore de trabalho. Modo: {mode}.\n\n"
        "As mesmas perguntas são fornecidas às três execuções. A seleção v5 anterior "
        "falha antes de consumir a primeira pergunta. Entrada automatizada; sem modelo "
        "simulado. O snapshot de abertura é público e real, quando presente; "
        "a sincronização de abertura é substituída pela reutilização desse snapshot. "
        "As consultas de estoque sob demanda usam a API real e o cache de contingência.\n\n"
        f"Snapshot consultado: `{snapshot['fetched_at_utc'] if snapshot else 'ausente'}`.\n\n"
        + "\n".join(reports)
    )
    path = ROOT / args.output
    path.write_text(text, encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
