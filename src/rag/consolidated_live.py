"""Shim de compatibilidade retroativa para ``rag.consolidated.live``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.consolidated.live import (
        _cache_path as _cache_path,
    )
    from rag.consolidated.live import (
        _ceaf_reply as _ceaf_reply,
    )
    from rag.consolidated.live import (
        _term as _term,
    )
    from rag.consolidated.live import (
        compatible_product as compatible_product,
    )
    from rag.consolidated.live import (
        lookup_stock as lookup_stock,
    )
    from rag.consolidated.live import (
        source_codes as source_codes,
    )
else:
    from rag.consolidated import live as _target

    sys.modules[__name__] = _target
