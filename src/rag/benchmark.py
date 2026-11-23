"""Shim de compatibilidade retroativa para ``rag.legacy.benchmark``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.legacy.benchmark import (
        RUBRIC_FIELDS as RUBRIC_FIELDS,
    )
    from rag.legacy.benchmark import (
        STATUSES as STATUSES,
    )
    from rag.legacy.benchmark import (
        _mean as _mean,
    )
    from rag.legacy.benchmark import (
        artifact_paths as artifact_paths,
    )
    from rag.legacy.benchmark import (
        dataset_hash as dataset_hash,
    )
    from rag.legacy.benchmark import (
        main as main,
    )
    from rag.legacy.benchmark import (
        read_jsonl as read_jsonl,
    )
    from rag.legacy.benchmark import (
        report_human_reviews as report_human_reviews,
    )
    from rag.legacy.benchmark import (
        run_benchmark as run_benchmark,
    )
    from rag.legacy.benchmark import (
        validate_cases as validate_cases,
    )
    from rag.legacy.benchmark import (
        write_artifacts as write_artifacts,
    )
else:
    from rag.legacy import benchmark as _target

    sys.modules[__name__] = _target
