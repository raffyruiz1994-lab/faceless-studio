"""Faceless Studio package init.

Sanitize bracketed IPv6 entries in no_proxy at import time: httpx (used by
google-genai) crashes building clients when no_proxy contains entries like
"[::1]". The proxy itself keeps working; only the malformed entries are dropped.
"""
from __future__ import annotations

import os

for _var in ("no_proxy", "NO_PROXY"):
    _val = os.environ.get(_var)
    if _val:
        _clean = ",".join(
            p for p in _val.split(",") if "[" not in p and not p.strip().startswith("::")
        )
        if _clean != _val:
            os.environ[_var] = _clean
