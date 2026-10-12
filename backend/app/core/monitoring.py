import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from app.core.config import settings
from app.core.logging import logger

SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-session-id",
    "proxy-authorization",
    "x-api-key",
}

SENSITIVE_KEY_PATTERNS = re.compile(
    r"(password|secret|token|api[_-]?key|auth|credit|card|credential|session)",
    re.IGNORECASE,
)

SENSITIVE_QUERY_PARAMS = {
    "x-amz-signature",
    "x-amz-credential",
    "x-amz-security-token",
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
}


def sanitize_url(raw_url: str | None) -> str | None:
    """Strips sensitive query parameters from URLs (e.g., presigned S3 URLs, auth tokens)."""
    if not raw_url:
        return raw_url
    try:
        parsed = urlparse(raw_url)
        if not parsed.query:
            return raw_url
        query_dict = parse_qs(parsed.query, keep_blank_values=True)
        sanitized_query = {}
        for k, vals in query_dict.items():
            if k.lower() in SENSITIVE_QUERY_PARAMS or SENSITIVE_KEY_PATTERNS.search(k):
                sanitized_query[k] = ["[FILTERED]"]
            else:
                sanitized_query[k] = vals
        new_query = urlencode(sanitized_query, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
    except Exception:
        return "[URL_SANITIZATION_ERROR]"


def sanitize_data_dict(data: Any, depth: int = 0) -> Any:
    """Recursively scrub sensitive keys and binary/PDF data from dictionaries or lists."""
    if depth > 8:
        return "[MAX_DEPTH_EXCEEDED]"
    if isinstance(data, dict):
        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            key_str = str(key)
            if SENSITIVE_KEY_PATTERNS.search(key_str):
                sanitized[key_str] = "[FILTERED]"
            elif isinstance(value, bytes | bytearray):
                sanitized[key_str] = f"[FILTERED_BINARY_{len(value)}_BYTES]"
            elif isinstance(value, dict | list):
                sanitized[key_str] = sanitize_data_dict(value, depth + 1)
            elif isinstance(value, str) and ("http://" in value or "https://" in value):
                sanitized[key_str] = sanitize_url(value)
            else:
                sanitized[key_str] = value
        return sanitized
    if isinstance(data, list):
        return [sanitize_data_dict(item, depth + 1) for item in data]
    if isinstance(data, str) and ("http://" in data or "https://" in data):
        return sanitize_url(data)
    if isinstance(data, bytes | bytearray):
        return f"[FILTERED_BINARY_{len(data)}_BYTES]"
    return data


def sentry_before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """
    Sentry before_send callback.
    Guarantees secrets, passwords, tokens, PDF contents, and binary blobs are scrubbed.
    """
    try:
        # Scrub request headers and body
        if "request" in event:
            req = event["request"]
            if "headers" in req and isinstance(req["headers"], dict):
                req["headers"] = {
                    k: ("[FILTERED]" if str(k).lower() in SENSITIVE_HEADERS else v)
                    for k, v in req["headers"].items()
                }

            if "url" in req and isinstance(req["url"], str):
                req["url"] = sanitize_url(req["url"])

            # Drop or scrub request body
            if "data" in req:
                content_type = str(req.get("headers", {}).get("Content-Type", "")).lower()
                if "multipart/form-data" in content_type or "pdf" in content_type or "octet-stream" in content_type:
                    req["data"] = "[FILTERED_UPLOAD_PAYLOAD]"
                else:
                    req["data"] = sanitize_data_dict(req["data"])

        # Scrub breadcrumbs
        if "breadcrumbs" in event and "values" in event["breadcrumbs"]:
            for bc in event["breadcrumbs"]["values"]:
                if "data" in bc:
                    if isinstance(bc["data"], dict) and "url" in bc["data"]:
                        bc["data"]["url"] = sanitize_url(bc["data"]["url"])
                    bc["data"] = sanitize_data_dict(bc["data"])

        # Scrub extra / contexts
        if "extra" in event:
            event["extra"] = sanitize_data_dict(event["extra"])

        return event
    except Exception as e:
        logger.warning(f"Error scrubbing Sentry event: {e}")
        return event


def sentry_before_breadcrumb(crumb: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Scrub breadcrumb URLs and metadata before collection."""
    try:
        if "data" in crumb and isinstance(crumb["data"], dict):
            if "url" in crumb["data"]:
                crumb["data"]["url"] = sanitize_url(crumb["data"]["url"])
            crumb["data"] = sanitize_data_dict(crumb["data"])
        return crumb
    except Exception:
        return crumb


def init_monitoring() -> None:
    """Initialize Sentry error tracking if configured via SENTRY_DSN."""
    if not settings.SENTRY_DSN:
        logger.info("Telemetry/Monitoring: SENTRY_DSN not configured; error tracking disabled.")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            before_send=sentry_before_send,
            before_breadcrumb=sentry_before_breadcrumb,
            send_default_pii=False,
            integrations=[
                FastApiIntegration(transaction_style="url"),
                CeleryIntegration(),
                SqlalchemyIntegration(),
            ],
        )
        logger.info(
            f"Telemetry/Monitoring: Initialized Sentry (environment={settings.SENTRY_ENVIRONMENT}, sample_rate={settings.SENTRY_TRACES_SAMPLE_RATE})"
        )
    except Exception as e:
        logger.error(f"Failed to initialize Sentry monitoring: {e}")
