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
