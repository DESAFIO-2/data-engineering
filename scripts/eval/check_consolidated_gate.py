"""Gate activation on frozen reviewed test cases and vector retrieval metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def check(paths: list[Path]) -> dict:
    results = {
        json.loads(path.read_bytes())["strategy"]: json.loads(path.read_bytes()) for path in paths
    }
    if set(results) != {"exact", "lexical", "vector", "hybrid"}:
        raise ValueError("Faltam resultados das quatro estratégias")
    reference = results["exact"]
    for name, result in results.items():
        if (
            result["split"] != "test"
            or result["dataset_sha256"] != reference["dataset_sha256"]
            or result["release_fingerprint"] != reference["release_fingerprint"]
        ):
            raise ValueError(f"Dataset ou release divergente: {name}")
        if result["reviewed_cases"] != result["cases"] or result["cases"] < 25:
            raise ValueError(f"Conjunto de teste sem revisão suficiente: {name}")
        if result["status_accuracy"] != 1:
            raise ValueError(f"Resposta de escopo incorreta: {name}")
    for name in ("vector", "hybrid"):
        result = results[name]
        if not result["embedding_model"] or result["hit_at_5"] < 0.9 or result["mrr_at_5"] < 0.8:
            raise ValueError(f"Meta vetorial não alcançada: {name}")
    return {
        "status": "passed",
        "release_fingerprint": reference["release_fingerprint"],
        "dataset_sha256": reference["dataset_sha256"],
        "strategies": {
            name: {
                "hit_at_5": r["hit_at_5"],
                "mrr_at_5": r["mrr_at_5"],
                "status_accuracy": r["status_accuracy"],
            }
            for name, r in results.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs=4, type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.results), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
