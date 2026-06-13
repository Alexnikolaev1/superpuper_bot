import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
    _client = None


async def request_with_retry(
    method: str,
    url: str,
    *,
    max_retries: int = 3,
    retry_statuses: frozenset[int] = frozenset({429, 500, 502, 503, 504}),
    **kwargs,
) -> httpx.Response:
    client = get_client()
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            resp = await client.request(method, url, **kwargs)
            if resp.status_code in retry_statuses and attempt < max_retries - 1:
                delay = 2 ** attempt
                logger.warning("Retry %s %s after %s (status %s)", method, url, delay, resp.status_code)
                await asyncio.sleep(delay)
                continue
            resp.raise_for_status()
            return resp
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError(f"Request failed: {method} {url}")
