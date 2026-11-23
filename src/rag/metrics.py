"""Shim de compatibilidade retroativa para ``rag.core.metrics``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.core.metrics import (
        PortugueseTokenizer as PortugueseTokenizer,
    )
    from rag.core.metrics import (
        percentile as percentile,
    )
    from rag.core.metrics import (
        retrieval_metrics as retrieval_metrics,
    )
    from rag.core.metrics import (
        strip_citations as strip_citations,
    )
    from rag.core.metrics import (
        text_metrics as text_metrics,
    )
else:
    from rag.core import metrics as _target

    sys.modules[__name__] = _target
