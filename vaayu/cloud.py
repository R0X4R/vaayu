from __future__ import annotations

from typing import Optional


def detect_scheme(uri: str) -> str:
    if "://" in uri:
        return uri.split("://", 1)[0].lower()
    return ""


def is_cloud_uri(uri: str) -> bool:
    return detect_scheme(uri) in {"s3", "gcs", "ftp"}


def not_implemented_for(scheme: Optional[str]) -> str:
    return f"Cloud scheme not implemented: {scheme}"
