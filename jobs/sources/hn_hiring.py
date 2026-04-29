from __future__ import annotations

from typing import Iterable

from jobs.models import Job
from jobs.sources.base import JobSourceBase


class HNHiringJobsSource(JobSourceBase):
    def run(self) -> Iterable[Job]:
        return []
