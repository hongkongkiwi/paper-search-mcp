import os
import time

import requests


def should_run_network_tests() -> bool:
    return os.environ.get("PYTEST_RUN_NETWORK") == "1"


def check_url_accessible(
    url: str,
    timeout: int = 5,
    retries: int = 1,
    retry_statuses: tuple[int, ...] = (),
    **kwargs,
) -> bool:
    if not should_run_network_tests():
        return False

    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout, **kwargs)
        except requests.RequestException:
            return False

        if response.status_code == 200:
            return True

        is_last_attempt = attempt == retries - 1
        if response.status_code not in retry_statuses or is_last_attempt:
            return False

        time.sleep(attempt + 1)

    return False
