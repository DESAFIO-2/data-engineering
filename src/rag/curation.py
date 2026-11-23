"""Shim de compatibilidade retroativa para ``rag.core.curation``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.core.curation import (
        _bytes as _bytes,
    )
    from rag.core.curation import (
        _current as _current,
    )
    from rag.core.curation import (
        _hash as _hash,
    )
    from rag.core.curation import (
        _pairs as _pairs,
    )
    from rag.core.curation import (
        _read as _read,
    )
    from rag.core.curation import (
        _safe as _safe,
    )
    from rag.core.curation import (
        _validate as _validate,
    )
    from rag.core.curation import (
        export_review as export_review,
    )
    from rag.core.curation import (
        load_approved as load_approved,
    )
    from rag.core.curation import (
        publish as publish,
    )
else:
    from rag.core import curation as _target

    sys.modules[__name__] = _target
