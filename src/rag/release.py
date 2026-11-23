"""Shim de compatibilidade retroativa para ``rag.legacy.release``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.legacy.release import (
        Release as Release,
    )
    from rag.legacy.release import (
        _rows as _rows,
    )
    from rag.legacy.release import (
        _text_hashes as _text_hashes,
    )
else:
    from rag.legacy import release as _target

    sys.modules[__name__] = _target
