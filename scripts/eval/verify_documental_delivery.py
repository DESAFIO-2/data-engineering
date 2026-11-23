"""Confere as citações exibidas pela CLI e exercita a troca de release lexical."""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from rag.consolidated import ConsolidatedRelease

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    cases = [
        json.loads(line)
        for line in (ROOT / "evals/datasets/week3_v9_test_reviewed.jsonl").read_text().splitlines()
    ]
    report = []
    for version in ("v9", "v8", "v9"):
        (folder,) = (ROOT / "data/releases").glob(
            f"corpus-consolidado-{version}-aprovado-*/release.json"
        )
        release = ConsolidatedRelease.load(folder.parent)
        records = []
        for case in cases:
            if version == "v8" and case["id"] != "W3-TEST-CAND-01":
                continue
            started = time.perf_counter()
            output = subprocess.run(
                [
                    sys.executable,
                    "app.py",
                    "ask",
                    case["question"],
                    "--documental",
                    "--strategy",
                    "lexical",
                    "--release",
                    str(folder.parent),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
                env={**os.environ, "APP_GOOGLE_API_KEY": ""},
            ).stdout
            refs = set(case["relevant_ids"])
            if case["id"].endswith("-10"):
                refs = {
                    e["evidence_id"]
                    for e in release.evidence
                    if e["active_ingredient"].casefold() == "ácido fólico"
                    and e["source"]["source_id"] == "F03"
                }
                assert len(refs) >= 2
            cited = set(re.findall(r"\bevidence-[0-9a-f]+\b", output))
            assert cited == refs, (case["id"], cited ^ refs)
            if case["id"].endswith("-03"):
                assert "Qual dessas apresentações" not in output and "uso tópico" not in output
            if refs:
                for eid in refs:
                    ev = next(e for e in release.evidence if e["evidence_id"] == eid)
                    assert any(
                        eid in line
                        and ev["source"]["version"] in line
                        and f"página {ev['source']['page']}" in line
                        for line in output.splitlines()
                    ), case["id"]
            if case["id"].endswith("-11"):
                assert "Não posso orientar dose" in output
            records.append(
                dict(
                    id=case["id"],
                    evidence_ids=sorted(cited),
                    output=output.strip(),
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                )
            )
        report.append(dict(release=release.fingerprint, version=version, records=records))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
