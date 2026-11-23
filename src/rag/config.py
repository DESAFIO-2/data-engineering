"""Shim de compatibilidade retroativa para ``rag.core.config``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.core.config import (
        DEFAULT_CHAT_MODEL as DEFAULT_CHAT_MODEL,
    )
    from rag.core.config import (
        DEFAULT_EMBEDDING_MODEL as DEFAULT_EMBEDDING_MODEL,
    )
    from rag.core.config import (
        DEFAULT_RELEASE_DIR as DEFAULT_RELEASE_DIR,
    )
    from rag.core.config import (
        DEFAULT_TOP_K as DEFAULT_TOP_K,
    )
    from rag.core.config import (
        DEFAULT_VECTOR_DIR as DEFAULT_VECTOR_DIR,
    )
    from rag.core.config import (
        ROOT as ROOT,
    )
    from rag.core.config import (
        Settings as Settings,
    )
    from rag.core.config import (
        _env as _env,
    )
    from rag.core.config import (
        get_settings as get_settings,
    )
else:
    from rag.core import config as _target

    sys.modules[__name__] = _target
