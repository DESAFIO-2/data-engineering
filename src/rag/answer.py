"""Shim de compatibilidade retroativa para ``rag.consolidated.answer``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.consolidated.answer import (
        _ROLE_PREFIX_RE as _ROLE_PREFIX_RE,
    )
    from rag.consolidated.answer import (
        SYSTEM as SYSTEM,
    )
    from rag.consolidated.answer import (
        _sanitize_untrusted_text as _sanitize_untrusted_text,
    )
    from rag.consolidated.answer import (
        synthesize as synthesize,
    )
else:
    from rag.consolidated import answer as _target

    sys.modules[__name__] = _target
