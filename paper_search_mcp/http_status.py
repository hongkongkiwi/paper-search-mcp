import requests


class HttpStatusError(RuntimeError):
    pass


def _message(context: str, response: requests.Response) -> str:
    reason = response.reason or ""
    if reason:
        return f"{context}: HTTP {response.status_code} {reason}"
    return f"{context}: HTTP {response.status_code}"


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
