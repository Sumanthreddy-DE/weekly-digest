from __future__ import annotations

from typing import Iterable

from jobs.models import Job
from jobs.sources.base import JobSourceBase


class WellfoundSource(JobSourceBase):
    def run(self) -> Iterable[Job]:
        return []
