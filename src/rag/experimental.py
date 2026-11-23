"""Shim de compatibilidade retroativa para ``rag.legacy.experimental``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.legacy.experimental import (
        CITATION as CITATION,
    )
    from rag.legacy.experimental import (
        CLINICAL as CLINICAL,
    )
    from rag.legacy.experimental import (
        PACKAGING_PAREN as PACKAGING_PAREN,
    )
    from rag.legacy.experimental import (
        SAFE_ABSTENTION as SAFE_ABSTENTION,
    )
    from rag.legacy.experimental import (
        STOP as STOP,
    )
    from rag.legacy.experimental import (
        STRENGTH as STRENGTH,
    )
    from rag.legacy.experimental import (
        SYSTEM as SYSTEM,
    )
    from rag.legacy.experimental import (
        Corpus as Corpus,
    )
    from rag.legacy.experimental import (
        Retriever as Retriever,
    )
    from rag.legacy.experimental import (
        build_index as build_index,
    )
    from rag.legacy.experimental import (
        compound_strength_in_query as compound_strength_in_query,
    )
    from rag.legacy.experimental import (
        generate as generate,
    )
    from rag.legacy.experimental import (
        has_strength as has_strength,
    )
    from rag.legacy.experimental import (
        has_term as has_term,
    )
    from rag.legacy.experimental import (
        index_location as index_location,
    )
    from rag.legacy.experimental import (
        name_in_query as name_in_query,
    )
    from rag.legacy.experimental import (
        open_index as open_index,
    )
    from rag.legacy.experimental import (
        rows as rows,
    )
    from rag.legacy.experimental import (
        strength_components as strength_components,
    )
    from rag.legacy.experimental import (
        strength_key as strength_key,
    )
    from rag.legacy.experimental import (
        strip_packaging_note as strip_packaging_note,
    )
    from rag.legacy.experimental import (
        tokens as tokens,
    )
    from rag.legacy.experimental import (
        vector_store as vector_store,
    )
else:
    from rag.legacy import experimental as _target

    sys.modules[__name__] = _target
