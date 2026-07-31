import hashlib
import json
from collections.abc import Mapping
from typing import Any


def deterministic_key(namespace: str, values: Mapping[str, Any]) -> str:
    """Create a stable key from a namespace and canonical JSON payload."""
    canonical = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(f"{namespace}:{canonical}".encode()).hexdigest()
    return f"{namespace}:{digest}"
