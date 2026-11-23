"""Create a reviewable CSV from independent source-alignment findings."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FIELDS = (
    "occurrence_id",
    "source",
    "page",
    "row",
    "field",
    "published",
    "extracted",
    "decision",
    "justification",
    "reviewer",
    "reviewed_at",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.findings.read_text(encoding="utf-8"))
    with args.output.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for finding in payload["findings"]:
            writer.writerow(finding)
    print(f"{len(payload['findings'])} diferenças preparadas em {args.output}")


if __name__ == "__main__":
    main()
