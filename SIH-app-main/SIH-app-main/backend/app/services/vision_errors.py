BUSY_STATUS_CODES = {429, 503}
BUSY_DETAIL = (
    "The AI server is currently busy due to high demand. Please try again in a few moments."
)


class VisionProviderBusyError(Exception):
    """Raised when every configured vision/OCR provider is rate-limited or unavailable."""

    def __init__(self, message: str = BUSY_DETAIL) -> None:
        super().__init__(message)


def is_provider_busy(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)
    if status is None:
        status = getattr(exc, "status", None)
    try:
        if int(status) in BUSY_STATUS_CODES:
            return True
    except (TypeError, ValueError):
        pass

    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None) if response is not None else None
    try:
        if int(response_status) in BUSY_STATUS_CODES:
            return True
    except (TypeError, ValueError):
        pass

    text = str(exc).upper()
    return any(
        token in text
        for token in (
            "429",
            "503",
            "UNAVAILABLE",
            "TOO MANY REQUESTS",
            "RESOURCE_EXHAUSTED",
            "RESOURCE EXHAUSTED",
            "RATE LIMIT",
            "TIMED OUT",
            "TIMEOUT",
        )
    )


def is_retryable_failure(exc: BaseException) -> bool:
    if is_provider_busy(exc):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    name = type(exc).__name__.lower()
    if "timeout" in name or "connect" in name:
        return True
    text = str(exc).lower()
    return any(token in text for token in ("timeout", "timed out", "connection reset", "temporarily"))
