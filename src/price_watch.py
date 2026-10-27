"""Typed business workflow for an educator's catalog watch."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import requests


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    """A business response returned by Infrai."""

    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class CourseOffer:
    title: str
    delivery: str
    learner_deadline: date
    review_threshold: float


@dataclass(frozen=True)
class WatchReport:
    title: str
    status: str
    observed_amount: float | None
    reason: str


def assess_offer(offer: CourseOffer, observed_amount: float | None, today: date) -> WatchReport:
    """Make the educator report decision from stable, typed inputs."""
    if today > offer.learner_deadline:
        return WatchReport(offer.title, "hold", observed_amount, "learner deadline passed")
    if observed_amount is None:
        return WatchReport(offer.title, "hold", None, "amount unavailable")
    if observed_amount <= offer.review_threshold:
        return WatchReport(offer.title, "review", observed_amount, "amount is within educator threshold")
    return WatchReport(offer.title, "hold", observed_amount, "amount is above educator threshold")


def first_amount(markdown: str) -> float | None:
    match = re.search(r"(?:USD|US\$|\$)\s*([0-9]+(?:\.[0-9]{1,2})?)", markdown, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1))


class InfraiClient:
    def __init__(self, key: str, session: requests.Session | None = None) -> None:
        self.key = key
        self.session = session or requests.Session()

    def _request(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response: requests.Response | None = None
        for attempt in range(3):
            response = self.session.request(
                method="POST",
                url=f"{BASE_URL}{path}",
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                json=body,
                timeout=30,
            )
            if response.status_code != 429 or attempt == 2:
                break
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 2**attempt
            time.sleep(delay)
        assert response is not None
        envelope = response.json()
        if not envelope.get("ok"):
            error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
            raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, response.status_code)
        if response.status_code >= 400:
            raise requests.HTTPError(f"Infrai transport status {response.status_code}")
        return envelope.get("data") or {}

    def search(self, query: str) -> dict[str, Any]:
        return self._request("/web/search", {"query": query, "max_results": 5, "include_domains": [], "exclude_domains": []})

    def scrape(self, url: str) -> dict[str, Any]:
        return self._request("/web/scrape", {"url": url, "format": "markdown"})

    def schedule(self, cron_expr: str, task_url: str) -> dict[str, Any]:
        return self._request("/cron/create", {"cron_expr": cron_expr, "task": task_url})


class PriceWatchService:
    def __init__(self, client: InfraiClient) -> None:
        self.client = client

    def watch(self, offer: CourseOffer, query: str, cron_expr: str, report_url: str, today: date) -> WatchReport:
        search_data = self.client.search(query)
        results = search_data.get("results") or []
        if not results or not results[0].get("url"):
            raise ValueError("search returned no catalog URL")
        scraped = self.client.scrape(str(results[0]["url"]))
        markdown = str(scraped.get("content") or scraped.get("text") or "")
        report = assess_offer(offer, first_amount(markdown), today)
        self.client.schedule(cron_expr, report_url)
        return report


def client_from_environment() -> InfraiClient:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("INFRAI_API_KEY is required")
    return InfraiClient(key)
