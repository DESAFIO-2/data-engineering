"""Shim de compatibilidade retroativa para ``rag.legacy.vector``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.legacy.vector import (
        _vectorstore as _vectorstore,
    )
    from rag.legacy.vector import (
        build_index as build_index,
    )
    from rag.legacy.vector import (
        index_location as index_location,
    )
    from rag.legacy.vector import (
        open_index as open_index,
    )
else:
    from rag.legacy import vector as _target

    sys.modules[__name__] = _target
