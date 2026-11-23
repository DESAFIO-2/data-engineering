"""Shim de compatibilidade retroativa para ``rag.core.table_extract``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.core.table_extract import (
        clean as clean,
    )
    from rag.core.table_extract import (
        reme_rows as reme_rows,
    )
    from rag.core.table_extract import (
        rename_rows as rename_rows,
    )
else:
    from rag.core import table_extract as _target

    sys.modules[__name__] = _target
