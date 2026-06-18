import uuid
from typing import Optional

from app.config import (
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_REGION,
    R2_ENDPOINT,
    R2_PUBLIC_BASE_URL,
)

_r2_client = None


def _get_r2_client():
    """
    Lazily create and cache an S3-compatible client for Cloudflare R2.
    Returns None if configuration is incomplete or a client cannot be created.
    """
    global _r2_client
    if _r2_client is not None:
        return _r2_client

    # Minimal config required to talk to R2
    if not (R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME):
        return None

    try:
        import boto3  # type: ignore
    except Exception:
        return None

    endpoint = R2_ENDPOINT or f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    region = R2_REGION or "auto"

    try:
        _r2_client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name=region,
        )
    except Exception:
        _r2_client = None
    return _r2_client


def _build_public_url(key: str) -> Optional[str]:
    """
    Build a public URL for an object key in R2.
    Prefer explicit R2_PUBLIC_BASE_URL if provided, otherwise fall back to
    bucket.accountid.r2.cloudflarestorage.com.
    """
    if not (R2_BUCKET_NAME and R2_ACCOUNT_ID):
        return None

    base = (R2_PUBLIC_BASE_URL or "").strip()
    if not base:
        base = f"https://{R2_BUCKET_NAME}.{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    # ensure no trailing slash
    if base.endswith("/"):
        base = base[:-1]
    return f"{base}/{key.lstrip('/')}"


def upload_image_bytes_to_r2(
    content: bytes,
    *,
    key_prefix: str = "",
    content_type: str = "image/png",
) -> Optional[str]:
    """
    Upload image bytes to Cloudflare R2 and return a public URL.
    Returns None if R2 is not configured or upload fails.
    """
    if not content:
        return None

    client = _get_r2_client()
    if client is None:
        return None

    # key like "generated/uuid.png" or "logos/uuid.png"
    key_parts = []
    if key_prefix:
        key_parts.append(key_prefix.strip("/"))
    key_parts.append(f"{uuid.uuid4().hex}.png")
    key = "/".join(key_parts)

    try:
        client.put_object(
            Bucket=R2_BUCKET_NAME,  # type: ignore[arg-type]
            Key=key,
            Body=content,
            ContentType=content_type or "image/png",
        )
    except Exception:
        return None

    return _build_public_url(key)

