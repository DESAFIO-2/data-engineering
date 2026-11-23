"""Shim de compatibilidade retroativa para ``rag.legacy.live``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.legacy.live import (
        BRT as BRT,
    )
    from rag.legacy.live import (
        PRODUCTS as PRODUCTS,
    )
    from rag.legacy.live import (
        _address as _address,
    )
    from rag.legacy.live import (
        _cnes as _cnes,
    )
    from rag.legacy.live import (
        _location_reply as _location_reply,
    )
    from rag.legacy.live import (
        _map_url as _map_url,
    )
    from rag.legacy.live import (
        _stamp as _stamp,
    )
    from rag.legacy.live import (
        _stock_reply as _stock_reply,
    )
    from rag.legacy.live import (
        _timestamp as _timestamp,
    )
    from rag.legacy.live import (
        _unit_line as _unit_line,
    )
    from rag.legacy.live import (
        live_reply as live_reply,
    )
    from rag.legacy.live import (
        load_snapshot as load_snapshot,
    )
    from rag.legacy.live import (
        stock_reply_for_product as stock_reply_for_product,
    )
else:
    from rag.legacy import live as _target

    sys.modules[__name__] = _target
