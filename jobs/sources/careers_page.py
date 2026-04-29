from __future__ import annotations

from typing import Iterable

from jobs.models import Job
from jobs.sources.base import JobSourceBase


class CareersPageSource(JobSourceBase):
    def __init__(self, config: dict, companies: list[dict]):
        super().__init__(config)
        self.companies = companies

    def run(self) -> Iterable[Job]:
        return []
