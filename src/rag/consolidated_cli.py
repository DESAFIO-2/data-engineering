"""Shim de compatibilidade retroativa para ``rag.cli.consolidated``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.cli.consolidated import (
        run as run,
    )
else:
    from rag.cli import consolidated as _target

    sys.modules[__name__] = _target
