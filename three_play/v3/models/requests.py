from typing import Optional, List

from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from ...config.requests import (
    DEFAULT_MAX_RETRIES, DEFAULT_BACKOFF_FACTOR, DEFAULT_STATUS_FORCE_LIST)


class SessionWithRetry(Session):

    def __init__(self, auth=None,
                 num_retries=DEFAULT_MAX_RETRIES,
                 backoff_factor=DEFAULT_BACKOFF_FACTOR,
                 additional_status_force_list: Optional[List[int]] = None):

        super().__init__()
        self.auth = auth

        status_force_list = DEFAULT_STATUS_FORCE_LIST
        # Retry on additional status codes (ex. HTTP 400) if needed
        if additional_status_force_list:
            status_force_list.extend(additional_status_force_list)

        retry_strategy = Retry(
            read=0,
            total=num_retries,
            status_forcelist=status_force_list,
            method_whitelist=["HEAD", "GET", "PUT", "POST", "DELETE", "OPTIONS", "TRACE"],
            backoff_factor=backoff_factor
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)

        self.mount("https://", adapter)
        self.mount("http://", adapter)
