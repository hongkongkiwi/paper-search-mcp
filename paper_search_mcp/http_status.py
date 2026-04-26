import requests


class HttpStatusError(RuntimeError):
    pass


SEMANTIC_SCHOLAR_429_NOTE = (
    "Semantic Scholar 429 rate limits are common because unauthenticated "
    "requests share a rate limit across all users. Trying again may work."
)


def _message(context: str, response: requests.Response) -> str:
    reason = response.reason or ""
    status = f"HTTP {response.status_code}"
    if reason:
        status = f"{status} {reason}"

    if response.status_code == 404:
        return f"{context}: resource not found ({status})"
    if response.status_code == 403:
        return f"{context}: access denied ({status})"
    if response.status_code == 429:
        if context.startswith("Semantic Scholar"):
            return f"{context}: rate limited ({status}). {SEMANTIC_SCHOLAR_429_NOTE}"
        return f"{context}: rate limited ({status})"
    if response.status_code >= 500:
        return f"{context}: remote service error ({status})"

    return f"{context}: {status}"


def raise_for_status(response: requests.Response, context: str) -> None:
    if response.status_code == 200:
        return
    raise HttpStatusError(_message(context, response))


def raise_if_http_error(error: Exception, context: str) -> None:
    if isinstance(error, HttpStatusError):
        raise error
    if isinstance(error, requests.RequestException) and error.response is not None:
        raise HttpStatusError(_message(context, error.response)) from error


def is_pdf_response(response: requests.Response) -> bool:
    if "application/pdf" in response.headers.get("Content-Type", ""):
        return True
    return response.content[:5] == b"%PDF-"


def non_pdf_error(response: requests.Response) -> str:
    content_type = response.headers.get("Content-Type", "unknown")
    return f"Error: URL returned non-PDF content (Content-Type: {content_type}). Paper may be paywalled or gated."
