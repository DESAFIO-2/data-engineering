"""Shim de compatibilidade retroativa para ``rag.core.conversation``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.core.conversation import (
        GREETINGS as GREETINGS,
    )
    from rag.core.conversation import (
        format_history as format_history,
    )
    from rag.core.conversation import (
        greeting_reply as greeting_reply,
    )
    from rag.core.conversation import (
        is_clarification as is_clarification,
    )
    from rag.core.conversation import (
        is_clarification_input as is_clarification_input,
    )
else:
    from rag.core import conversation as _target

    sys.modules[__name__] = _target
