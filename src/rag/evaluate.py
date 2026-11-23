"""Shim de compatibilidade retroativa para ``rag.legacy.evaluate``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.legacy.evaluate import (
        evaluate_retrieval as evaluate_retrieval,
    )
else:
    from rag.legacy import evaluate as _target

    sys.modules[__name__] = _target
