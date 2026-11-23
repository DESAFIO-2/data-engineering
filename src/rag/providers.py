"""Shim de compatibilidade retroativa para ``rag.core.providers``."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag.core.providers import (
        _KEY_AUTH_RE as _KEY_AUTH_RE,
    )
    from rag.core.providers import (
        _KEY_FAILOVER_MSG_RE as _KEY_FAILOVER_MSG_RE,
    )
    from rag.core.providers import (
        _KEY_FAILOVER_NAME_RE as _KEY_FAILOVER_NAME_RE,
    )
    from rag.core.providers import (
        _KEY_FAILOVER_STATUS_CODES as _KEY_FAILOVER_STATUS_CODES,
    )
    from rag.core.providers import (
        _PERMANENT_KEY_MSG_RE as _PERMANENT_KEY_MSG_RE,
    )
    from rag.core.providers import (
        _PERMANENT_KEY_STATUS_CODES as _PERMANENT_KEY_STATUS_CODES,
    )
    from rag.core.providers import (
        _PERMANENT_QUOTA_RE as _PERMANENT_QUOTA_RE,
    )
    from rag.core.providers import (
        _TRANSIENT_MSG_RE as _TRANSIENT_MSG_RE,
    )
    from rag.core.providers import (
        _TRANSIENT_NAME_RE as _TRANSIENT_NAME_RE,
    )
    from rag.core.providers import (
        _TRANSIENT_STATUS_CODES as _TRANSIENT_STATUS_CODES,
    )
    from rag.core.providers import (
        CachedQueryEmbeddings as CachedQueryEmbeddings,
    )
    from rag.core.providers import (
        _chain_matches as _chain_matches,
    )
    from rag.core.providers import (
        _exception_chain as _exception_chain,
    )
    from rag.core.providers import (
        _FailoverPool as _FailoverPool,
    )
    from rag.core.providers import (
        _FallbackChatModel as _FallbackChatModel,
    )
    from rag.core.providers import (
        _FallbackEmbeddings as _FallbackEmbeddings,
    )
    from rag.core.providers import (
        _is_permanent_key_failure as _is_permanent_key_failure,
    )
    from rag.core.providers import (
        _retry_delay_seconds as _retry_delay_seconds,
    )
    from rag.core.providers import (
        _status_code as _status_code,
    )
    from rag.core.providers import (
        error_detail as error_detail,
    )
    from rag.core.providers import (
        google_chat as google_chat,
    )
    from rag.core.providers import (
        google_embeddings as google_embeddings,
    )
    from rag.core.providers import (
        invoke_with_retry as invoke_with_retry,
    )
    from rag.core.providers import (
        is_key_failover_error as is_key_failover_error,
    )
    from rag.core.providers import (
        is_transient_provider_error as is_transient_provider_error,
    )
    from rag.core.providers import (
        normalize_api_keys as normalize_api_keys,
    )
else:
    from rag.core import providers as _target

    sys.modules[__name__] = _target
