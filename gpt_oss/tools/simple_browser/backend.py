"""
Simple backend for the simple browser tool.
"""

import functools
import logging
import os
from abc import abstractmethod
from typing import Callable, ParamSpec, TypeVar
from urllib.parse import quote

import chz
from aiohttp import ClientSession, ClientTimeout
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .page_contents import (
    Extract,
    FetchResult,
    PageContents,
    get_domain,
    process_html,
)

logger = logging.getLogger(__name__)


VIEW_SOURCE_PREFIX = "view-source:"


class BackendError(Exception):
    pass


P = ParamSpec("P")
R = TypeVar("R")


def with_retries(
    func: Callable[P, R],
    num_retries: int,
    max_wait_time: float,
) -> Callable[P, R]:
    if num_retries > 0:
        retry_decorator = retry(
            stop=stop_after_attempt(num_retries),
            wait=wait_exponential(
                multiplier=1,
                min=2,
                max=max_wait_time,
            ),
            before_sleep=before_sleep_log(logger, logging.INFO),
            after=after_log(logger, logging.INFO),
            retry=retry_if_exception_type(Exception),
        )
        return retry_decorator(func)
    else:
        return func


def maybe_truncate(text: str, num_chars: int = 1024) -> str:
    if len(text) > num_chars:
        text = text[: (num_chars - 3)] + "..."
    return text


@chz.chz(typecheck=True)
class Backend:
    source: str = chz.field(doc="Description of the backend source")

    @abstractmethod
    async def search(
        self,
        query: str,
        topn: int,
        session: ClientSession,
    ) -> PageContents:
        pass

    @abstractmethod
    async def fetch(self, url: str, session: ClientSession) -> PageContents:
        pass


@chz.chz(typecheck=True)
class ExaBackend(Backend):
    """Backend that uses the Exa Search API."""

    source: str = chz.field(doc="Description of the backend source")
    api_key: str | None = chz.field(
        doc="Exa API key. Uses EXA_API_KEY environment variable if not provided.",
        default=None,
    )

    BASE_URL: str = "https://api.exa.ai"

    def _get_api_key(self) -> str:
        key = self.api_key or os.environ.get("EXA_API_KEY")
        if not key:
            raise BackendError("Exa API key not provided")
        return key

    async def _post(self, session: ClientSession, endpoint: str, payload: dict) -> dict:
        headers = {"x-api-key": self._get_api_key()}
        async with session.post(f"{self.BASE_URL}{endpoint}", json=payload, headers=headers) as resp:
            if resp.status != 200:
                raise BackendError(
                    f"Exa API error {resp.status}: {await resp.text()}"
                )
            return await resp.json()

    async def search(
        self, query: str, topn: int, session: ClientSession
    ) -> PageContents:
        data = await self._post(
            session,
            "/search",
            {"query": query, "numResults": topn, "contents": {"text": True, "summary": True}},
        )
        # make a simple HTML page to work with browser format
        titles_and_urls = [
            (result["title"], result["url"], result["summary"]) 
            for result in data["results"]
        ]
        html_page = f"""
<html><body>
<h1>Search Results</h1>
<ul>
{"".join([f"<li><a href='{url}'>{title}</a> {summary}</li>" for title, url, summary in titles_and_urls])}
</ul>
</body></html>
"""

        return process_html(
            html=html_page,
            url="",
            title=query,
            display_urls=True,
            session=session,
        )

    async def fetch(self, url: str, session: ClientSession) -> PageContents:
        is_view_source = url.startswith(VIEW_SOURCE_PREFIX)
        if is_view_source:
            url = url[len(VIEW_SOURCE_PREFIX) :]
        data = await self._post(
            session,
            "/contents",
            {"urls": [url], "text": { "includeHtmlTags": True }},
        )
        results = data.get("results", [])
        if not results:
            raise BackendError(f"No contents returned for {url}")
        return process_html(
            html=results[0].get("text", ""),
            url=url,
            title=results[0].get("title", ""),
            display_urls=True,
            session=session,
        )


@chz.chz(typecheck=True)
class SearxBackend(Backend):
    """Backend that uses a SearxNG instance for search and direct HTTP fetch for contents."""

    source: str = chz.field(doc="Description of the backend source")
    searx_url: str | None = chz.field(
        doc="Base URL of SearxNG. Uses SEARXNG_URL env var if not provided.",
        default=None,
    )
    user_agent: str = chz.field(
        doc="User-Agent header for fetch requests.",
        default="Mozilla/5.0 (compatible; gpt-oss-simple-browser/1.0; +https://github.com/openai/gpt-oss)",
    )

    def _get_base_url(self) -> str:
        base = (self.searx_url or os.environ.get("SEARXNG_URL") or "http://server:8088").rstrip("/")
        return base

    async def search(self, query: str, topn: int, session: ClientSession) -> PageContents:
        params = {
            "q": query,
            "format": "json",
            # Keep categories generic; users can override via query syntax if needed
            "categories": "general",
        }
        url = f"{self._get_base_url()}/search"
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                raise BackendError(f"Searx error {resp.status}: {await resp.text()}")
            data = await resp.json()
        results = data.get("results", [])[:topn]
        titles_and_urls = [
            (
                r.get("title") or r.get("url", ""),
                r.get("url", ""),
                r.get("content", ""),
            )
            for r in results
            if r.get("url")
        ]
        html_page = f"""
<html><body>
<h1>Search Results</h1>
<ul>
{"".join([f"<li><a href='{url}'>{title}</a> {summary}</li>" for title, url, summary in titles_and_urls])}
</ul>
</body></html>
        """
        logger.info(f"Searx search results: {html_page}")

        return process_html(
            html=html_page,
            url="",
            title=query,
            display_urls=True,
            session=session,
        )

    async def fetch(self, url: str, session: ClientSession) -> PageContents:
        is_view_source = url.startswith(VIEW_SOURCE_PREFIX)
        if is_view_source:
            url = url[len(VIEW_SOURCE_PREFIX):]
        headers = {"User-Agent": self.user_agent}
        timeout = ClientTimeout(total=30)
        async with session.get(url, headers=headers, timeout=timeout, allow_redirects=True) as resp:
            if resp.status != 200:
                # Try to include a small body excerpt in error
                body = await resp.text()
                raise BackendError(f"Fetch error {resp.status} for {url}: {maybe_truncate(body, 500)}")
            html = await resp.text()
        return process_html(
            html=html,
            url=url,
            title=url,
            display_urls=True,
            session=session,
        )
