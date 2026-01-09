"""Hashing utilities."""

import hashlib
from typing import Union


def content_hash(content: Union[str, bytes]) -> str:
    """Generate a SHA-256 hash of content.

    Args:
        content: String or bytes to hash

    Returns:
        Hex-encoded hash string
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()
