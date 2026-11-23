"""Shim de compatibilidade retroativa para ``rag.consolidated.chat``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.consolidated.chat import (
        BLOCKED as BLOCKED,
    )
    from rag.consolidated.chat import (
        _documental as _documental,
    )
    from rag.consolidated.chat import (
        ask as ask,
    )
    from rag.consolidated.chat import (
        chat as chat,
    )
    from rag.consolidated.chat import (
        sync_live as sync_live,
    )
    from rag.consolidated.chat import (
        validated_products as validated_products,
    )
    from rag.consolidated.state import (
        REGIONS as REGIONS,
    )
    from rag.consolidated.state import (
        SOURCE_NAMES as SOURCE_NAMES,
    )
    from rag.consolidated.state import (
        ConversationState as ConversationState,
    )
    from rag.consolidated.state import (
        region_in as region_in,
    )
    from rag.consolidated.state import (
        stock_intent as stock_intent,
    )
else:
    from rag.consolidated import chat as _target

    sys.modules[__name__] = _target
