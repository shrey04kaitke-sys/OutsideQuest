"""Deployment mode detection.

Public mode is for shared hosting (e.g. Render). Streamlit sessions on a public host
must never read or write a shared personal JSON file, so persistent progress and
journal features are disabled there. Local development keeps full persistence.
"""

from __future__ import annotations

import os

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def is_public_mode() -> bool:
    """True when OUTSIDEQUEST_PUBLIC_MODE is truthy, or on Render when unset.

    An explicit false value overrides Render auto-detection (for example, a private
    single-user instance with its own disk).
    """
    explicit = os.getenv("OUTSIDEQUEST_PUBLIC_MODE", "").strip().lower()
    if explicit in _TRUE:
        return True
    if explicit in _FALSE:
        return False
    return os.getenv("RENDER", "").strip().lower() == "true"
