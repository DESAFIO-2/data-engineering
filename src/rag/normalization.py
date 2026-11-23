"""Shim de compatibilidade retroativa para ``rag.core.normalization``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.core.normalization import (
        _ABSENT as _ABSENT,
    )
    from rag.core.normalization import (
        _ATC_HERBAL as _ATC_HERBAL,
    )
    from rag.core.normalization import (
        _ATC_PARTIAL as _ATC_PARTIAL,
    )
    from rag.core.normalization import (
        _ATC_WHO as _ATC_WHO,
    )
    from rag.core.normalization import (
        _NBSP as _NBSP,
    )
    from rag.core.normalization import (
        _NOTE_MARK_RE as _NOTE_MARK_RE,
    )
    from rag.core.normalization import (
        _NUM as _NUM,
    )
    from rag.core.normalization import (
        _RELEASE_RATE_RE as _RELEASE_RATE_RE,
    )
    from rag.core.normalization import (
        _SALT_PAREN_RE as _SALT_PAREN_RE,
    )
    from rag.core.normalization import (
        _UNIT_TOKEN_RE as _UNIT_TOKEN_RE,
    )
    from rag.core.normalization import (
        NORMALIZATION_SCHEMA as NORMALIZATION_SCHEMA,
    )
    from rag.core.normalization import (
        VOCAB_FILES as VOCAB_FILES,
    )
    from rag.core.normalization import (
        RuleTrace as RuleTrace,
    )
    from rag.core.normalization import (
        Vocabulary as Vocabulary,
    )
    from rag.core.normalization import (
        _accent_count as _accent_count,
    )
    from rag.core.normalization import (
        _clean_spaces as _clean_spaces,
    )
    from rag.core.normalization import (
        _ingredient_surface as _ingredient_surface,
    )
    from rag.core.normalization import (
        build_ingredient_map as build_ingredient_map,
    )
    from rag.core.normalization import (
        canonical_form as canonical_form,
    )
    from rag.core.normalization import (
        canonical_ingredient as canonical_ingredient,
    )
    from rag.core.normalization import (
        canonical_release as canonical_release,
    )
    from rag.core.normalization import (
        canonical_strength as canonical_strength,
    )
    from rag.core.normalization import (
        check_bundle as check_bundle,
    )
    from rag.core.normalization import (
        fold as fold,
    )
    from rag.core.normalization import (
        identity_key as identity_key,
    )
    from rag.core.normalization import (
        load_vocabulary as load_vocabulary,
    )
    from rag.core.normalization import (
        normalize_occurrence as normalize_occurrence,
    )
    from rag.core.normalization import (
        parse_atc as parse_atc,
    )
    from rag.core.normalization import (
        parse_channel as parse_channel,
    )
    from rag.core.normalization import (
        vocabulary_bundle as vocabulary_bundle,
    )
else:
    from rag.core import normalization as _target

    sys.modules[__name__] = _target
