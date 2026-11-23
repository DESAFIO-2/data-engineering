"""Shim de compatibilidade retroativa para ``rag.legacy.retrieval``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.legacy.retrieval import (
        FORM_EXAMPLES as FORM_EXAMPLES,
    )
    from rag.legacy.retrieval import (
        FORM_TERMS as FORM_TERMS,
    )
    from rag.legacy.retrieval import (
        LIQUID_FORMS as LIQUID_FORMS,
    )
    from rag.legacy.retrieval import (
        TOPICAL_FORMS as TOPICAL_FORMS,
    )
    from rag.legacy.retrieval import (
        Match as Match,
    )
    from rag.legacy.retrieval import (
        _available_forms as _available_forms,
    )
    from rag.legacy.retrieval import (
        _form_matches as _form_matches,
    )
    from rag.legacy.retrieval import (
        _has_term as _has_term,
    )
    from rag.legacy.retrieval import (
        match_medicine as match_medicine,
    )
    from rag.legacy.retrieval import (
        normalize as normalize,
    )
    from rag.legacy.retrieval import (
        retrieve as retrieve,
    )
    from rag.legacy.retrieval import (
        retrieve_lexical as retrieve_lexical,
    )
else:
    from rag.legacy import retrieval as _target

    sys.modules[__name__] = _target
