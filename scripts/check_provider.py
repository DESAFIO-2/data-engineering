"""Diagnóstico com texto sintético; nunca imprime chave nem contexto de usuário."""

from __future__ import annotations

import argparse
import json

from rag.config import ROOT, get_settings
from rag.providers import google_embeddings


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", action="store_true")
    args = parser.parse_args()
    try:
        provider = google_embeddings(settings.rag_embedding_model, settings.google_api_key)
        if args.index:
            from rag.experimental import Corpus, build_index

            corpus = Corpus.load(
                ROOT / "data/corpus/experimental", ROOT / "data/raw/complementares/chunks.jsonl"
            )
            vector_base = (
                ROOT / settings.rag_vector_dir
                if corpus.manifest.get("restoration")
                else ROOT / "guia" / "vetorizacao-nova"
            )
            location = build_index(
                corpus,
                vector_base,
                settings.rag_embedding_model,
                provider,
                batch_size=8,
                requests_per_minute=90,
            )
            print(json.dumps({"index": str(location), "chunks": len(corpus.chunks)}))
            return 0
        vector = provider.embed_query("Teste sintético de indexação documental.")
        print(json.dumps({"model": settings.rag_embedding_model, "dimension": len(vector)}))
        return 0
    except Exception as exc:
        message = str(exc)
        if settings.google_api_key:
            message = message.replace(settings.google_api_key, "[REDACTED]")
        print(
            json.dumps({"error": type(exc).__name__, "detail": message[:1600]}, ensure_ascii=False)
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
