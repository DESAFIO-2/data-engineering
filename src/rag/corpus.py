"""Shim de compatibilidade retroativa para ``rag.core.corpus``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.core.corpus import (
        CODE as CODE,
    )
    from rag.core.corpus import (
        DOSE as DOSE,
    )
    from rag.core.corpus import (
        FORM as FORM,
    )
    from rag.core.corpus import (
        ITEM as ITEM,
    )
    from rag.core.corpus import (
        MANIFEST_PATH as MANIFEST_PATH,
    )
    from rag.core.corpus import (
        PARSER_VERSION as PARSER_VERSION,
    )
    from rag.core.corpus import (
        PARSERS as PARSERS,
    )
    from rag.core.corpus import (
        SCHEMA_VERSION as SCHEMA_VERSION,
    )
    from rag.core.corpus import (
        SOURCE_VERSIONS as SOURCE_VERSIONS,
    )
    from rag.core.corpus import (
        build_corpus as build_corpus,
    )
    from rag.core.corpus import (
        compact as compact,
    )
    from rag.core.corpus import (
        digest as digest,
    )
    from rag.core.corpus import (
        fields as fields,
    )
    from rag.core.corpus import (
        parse_f01 as parse_f01,
    )
    from rag.core.corpus import (
        parse_f03 as parse_f03,
    )
    from rag.core.corpus import (
        parse_f04 as parse_f04,
    )
    from rag.core.corpus import (
        split_pf_heading as split_pf_heading,
    )
    from rag.core.corpus import (
        split_text as split_text,
    )
    from rag.core.corpus import (
        stable_id as stable_id,
    )
else:
    from rag.core import corpus as _target

    sys.modules[__name__] = _target
