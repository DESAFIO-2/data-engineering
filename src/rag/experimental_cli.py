"""Shim de compatibilidade retroativa para ``rag.cli.experimental``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.cli.experimental import (
        corpus_supplement as corpus_supplement,
    )
    from rag.cli.experimental import (
        follow_up as follow_up,
    )
    from rag.cli.experimental import (
        open_validated_vectors as open_validated_vectors,
    )
    from rag.cli.experimental import (
        resolve as resolve,
    )
    from rag.cli.experimental import (
        run as run,
    )
    from rag.cli.experimental import (
        show as show,
    )
else:
    from rag.cli import experimental as _target

    sys.modules[__name__] = _target
