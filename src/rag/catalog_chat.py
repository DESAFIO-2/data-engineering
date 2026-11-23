"""Shim de compatibilidade retroativa para ``rag.consolidated.catalog``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.consolidated.catalog import (
        _browse_base as _browse_base,
    )
    from rag.consolidated.catalog import (
        _strength_order as _strength_order,
    )
    from rag.consolidated.catalog import (
        candidates as candidates,
    )
    from rag.consolidated.catalog import (
        catalog_item_name_matches as catalog_item_name_matches,
    )
    from rag.consolidated.catalog import (
        catalog_name_matches as catalog_name_matches,
    )
    from rag.consolidated.catalog import (
        options_reply as options_reply,
    )
    from rag.consolidated.catalog import (
        presentation_query as presentation_query,
    )
    from rag.consolidated.catalog import (
        stock_candidates as stock_candidates,
    )
else:
    from rag.consolidated import catalog as _target

    sys.modules[__name__] = _target
