"""Shim de compatibilidade retroativa para ``rag.consolidated.evaluation``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.consolidated.evaluation import (
        V7 as V7,
    )
    from rag.consolidated.evaluation import (
        _git_revision as _git_revision,
    )
    from rag.consolidated.evaluation import (
        _percentile as _percentile,
    )
    from rag.consolidated.evaluation import (
        _preflight as _preflight,
    )
    from rag.consolidated.evaluation import (
        _review_hash as _review_hash,
    )
    from rag.consolidated.evaluation import (
        _source_filter as _source_filter,
    )
    from rag.consolidated.evaluation import (
        _trace_candidates as _trace_candidates,
    )
    from rag.consolidated.evaluation import (
        evaluate as evaluate,
    )
else:
    from rag.consolidated import evaluation as _target

    sys.modules[__name__] = _target
