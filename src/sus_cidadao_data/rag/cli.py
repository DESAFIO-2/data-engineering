from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from sus_cidadao_data.rag.pipeline import (
    build_pipeline,
    load_built_index,
    repository_root,
    search_index,
)


def default_config_path() -> Path:
    return repository_root() / "config" / "rag_sources.json"


def default_output_dir() -> Path:
    return repository_root() / ".artifacts" / "rag"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pipeline local de recuperação do SUS Cidadão")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Extrai, fragmenta e indexa o corpus")
    build.add_argument("--config", type=Path, default=default_config_path())
    build.add_argument("--output", type=Path, default=default_output_dir())

    search = subparsers.add_parser("search", help="Busca trechos no índice construído")
    search.add_argument("query", help="Pergunta ou termos de busca")
    search.add_argument("--top-k", type=int, default=5)
    search.add_argument("--output", type=Path, default=default_output_dir())
    search.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "build":
        summary = build_pipeline(args.config.resolve(), args.output.resolve())
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
        return

    chunks, index = load_built_index(args.output.resolve())
    results = search_index(args.query, chunks=chunks, index=index, top_k=args.top_k)
    if args.as_json:
        print(
            json.dumps(
                [{"score": result.score, "chunk": asdict(result.chunk)} for result in results],
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if not results:
        print("Nenhuma evidência encontrada no corpus para esta consulta.")
        return
    for position, result in enumerate(results, start=1):
        chunk = result.chunk
        print(
            f"[{position}] score={result.score:.4f} | {chunk.title} | "
            f"versão={chunk.version} | página={chunk.page} | chunk={chunk.chunk_id}"
        )
        print(chunk.text)
        print()


if __name__ == "__main__":
    main()
