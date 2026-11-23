"""Validate explicit metformin UBS links against the public catalog and approved v5."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from ingestion.infosaude_live import UBS_URL, InfoSaudeLiveClient
from rag.config import ROOT
from rag.consolidated import ConsolidatedRelease, ingredient_key, normalize


def main() -> None:
    release = ConsolidatedRelease.load(
        ROOT / "data/releases/corpus-consolidado-v5-aprovado-2026-11-10"
    )
    catalog = InfoSaudeLiveClient().discover_ubs_products("metformina")
    expected = {
        "90224": ("METFORMINA (CLORIDRATO) COMPRIMIDO 500MG", "500 mg"),
        "90226": ("METFORMINA (CLORIDRATO) COMPRIMIDO 850 MG", "850 mg"),
    }
    by_code = {str(row["i_cod_produto"]): row["i_desc_produto"] for row in catalog}
    links = []
    stamp = datetime.now(UTC).isoformat()
    for code, (description, strength) in expected.items():
        if normalize(by_code.get(code, "")) != normalize(description):
            raise ValueError(
                f"Código UBS {code} ausente ou descrição divergente; arquivo preservado"
            )
        for medicine in release.catalog:
            if (
                ingredient_key(medicine["active_ingredient"]) == "cloridrato de metformina"
                and normalize(medicine["strength"]) == normalize(strength)
                and medicine["form"] == "comprimido"
                and medicine.get("release_characteristic") is None
            ):
                links.append(
                    {
                        **{
                            key: medicine.get(key)
                            for key in (
                                "medicine_id",
                                "active_ingredient",
                                "strength",
                                "form",
                                "release_characteristic",
                            )
                        },
                        "product_code": code,
                        "product_description": by_code[code],
                        "status": "validated",
                        "source_url": UBS_URL,
                        "validated_at": stamp,
                        "validation": (
                            "Código e descrição públicos; mesmo sal, concentração "
                            "e forma explícitos; "
                            "sem liberação modificada documentada."
                        ),
                    }
                )
    if len(links) != 3:
        raise ValueError("Apresentações v5 divergentes; arquivo preservado")
    payload = {
        "schema_version": "ubs-consolidated-links-v1",
        "release_fingerprint": release.fingerprint,
        "source_url": UBS_URL,
        "validated_at": stamp,
        "catalog": catalog,
        "links": links,
        "excluded": [
            {
                "code": "13142",
                "reason": (
                    "Ação prolongada: F04 não documenta forma farmacêutica; vínculo não habilitado."
                ),
            },
            {
                "reason": (
                    "Associações com outros princípios ativos "
                    "não correspondem à metformina isolada."
                )
            },
        ],
    }
    path = ROOT / "data/mappings/ubs_consolidated.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    print(f"Validados {len(links)} vínculos para códigos 90224 e 90226: {path}")


if __name__ == "__main__":
    main()
